import os
from collections import defaultdict
from typing import Dict, List, Tuple
from datetime import datetime, timedelta, timezone

from loguru import logger

from hazut_hakol.algo.geo_utils.polygon_set_cover import greedy_sweep_cover
from hazut_hakol.apio.barak_interfaces import BarakMetadataFetcher
from hazut_hakol.apio.knowledge_center.knowledge_center import KnowledgeCenter
from hazut_hakol.core.classes.roi import Roi, RoiRunningMode
from hazut_hakol.core.classes.trigger import Trigger, TriggerStatus, TriggerType
from ..entrex_context.entrex_context import EntrexProjectContext
from ..entrex_graph_system.entrex_graph import EntrexGraph

OPTIMIZATION_MIN_SIZE = 200
OPTIMIZATION_MAX_WAIT_SECONDS = 60 * 30


class EntrexGraphTriggerFactory:
    def __init__(self, entrex_project_context: EntrexProjectContext, entrex_graph: EntrexGraph,
                 knowledge_center: KnowledgeCenter, barak_metadata_fetcher: BarakMetadataFetcher):
        self._entrex_project_context = entrex_project_context
        self._entrex_graph = entrex_graph
        self._knowledge_cener = knowledge_center
        self._barak_metadata_fetcher = barak_metadata_fetcher

    def create_triggers_from_sweep_id_to_roi_mapping(
            self,
            sweep_id_to_rois_seeing_mapping: Dict[str, List[Roi]]
    ):
        logger.debug(f"Requesting creation of triggers for {len(sweep_id_to_rois_seeing_mapping)} sweep ids.")
        mapping_trigger_and_taskor_to_roi_list_and_prio = {}

        for trigger_id, list_of_rois in sweep_id_to_rois_seeing_mapping.items():
            taskor_names_to_roi_dict = self._transform_to_taskor_to_roi_dict(list_of_rois)
            priority_for_triggers = min([roi.priority for roi in list_of_rois])
            for taskor_name, taskor_rois in taskor_names_to_roi_dict.items():
                key = (trigger_id, taskor_name)
                mapping_trigger_and_taskor_to_roi_list_and_prio[key] = (taskor_rois, priority_for_triggers)

        logger.debug(f"Possible {len(mapping_trigger_and_taskor_to_roi_list_and_prio)} triggers needing update or creation")

        trigger_ids = list(set(trigger_id for trigger_id, _ in sweep_id_to_rois_seeing_mapping.items()))
        triggers = self._create_or_update_triggers(
            triggers_ids=trigger_ids,
            mapping_trigger_and_taskor_to_roi_list_and_prio=mapping_trigger_and_taskor_to_roi_list_and_prio
        )
        logger.debug(f"Returned {len(mapping_trigger_and_taskor_to_roi_list_and_prio)} triggers needing update or creation")
        return triggers

    def _transform_to_taskor_to_roi_dict(self, list_of_rois: List[Roi]) -> Dict[str, List[str]]:
        taskor_names_to_roi_dict = defaultdict(list)
        for roi in list_of_rois:
            project_name = roi.project_name
            project_taskor_names = self._entrex_graph.get_all_taskors_of_project(project_name=project_name)
            for taskor_name in project_taskor_names:
                taskor_names_to_roi_dict[taskor_name].append(roi)
        return taskor_names_to_roi_dict

    def _create_or_update_triggers(
            self,
            trigger_ids: List[str],
            mapping_trigger_and_taskor_to_roi_list_and_prio: Dict[Tuple[str, str], Tuple[List[Roi], int]]
    ) -> List[Trigger]:
        existing_triggers = self._knowledge_cener.trigger_db_interface.find_triggers_for_ids(trigger_ids=trigger_ids)
        mapping_existing_triggers = {(trigger.trigger_id, trigger.taskor_name): trigger for trigger in existing_triggers}

        new_triggers = []
        created_triggers_count = 0
        updated_triggers_count = 0

        for key, values in mapping_trigger_and_taskor_to_roi_list_and_prio.items():
            trigger_id, taskor_name = key
            rois, priority_for_trigger = values

            existing_trigger = mapping_existing_triggers.get(key, None)
            if existing_trigger is None:
                trigger = self._create_trigger(priority_for_trigger, rois, taskor_name, trigger_id,
                                               mapping_existing_triggers)
                created_triggers_count += 1
            else:
                trigger = self._update_trigger(existing_trigger, priority_for_trigger, rois, mapping_existing_triggers)
                updated_triggers_count += 1

            new_triggers.append(trigger)
        logger.debug(f"Needing {created_triggers_count} creations, and {updated_triggers_count} updates.")
        return new_triggers

    def _update_triggers(self, existing_trigger: Trigger, priority_for_trigger: int, new_rois: List[Roi],
                         mapping_existing_triggers) -> Trigger:
        existing_trigger.priority = min(existing_trigger.priority, priority_for_trigger)
        existing_trigger.rois = list(set(existing_trigger.rois) | set(new_rois))

        if existing_trigger.status in [TriggerStatus.FAILED, TriggerStatus.ABORTED, TriggerStatus.RESULTS_EXPIRED,
                                       TriggerStatus.SKIPPED]:
            existing_trigger.status = self._compute_trigger_status(
                existing_trigger.taskor_name, existing_trigger.trigger_id, existing_trigger.rois,
                mapping_existing_triggers, existing_trigger=True
            )
            existing_trigger.is_orchestartor_processed = False
        return existing_trigger

    def _create_trigger(self, priority_for_trigger: int, new_rois: List[Roi], taskor_name: str,
                        trigger_id: str, mapping_existing_triggers) -> Trigger:
        trigger_type = TriggerType.SWEEP
        trigger_status = self._compute_trigger_status(
            taskor_name, trigger_id, new_rois, mapping_existing_triggers
        )
        trigger = Trigger.create_new(
            taskor_name=taskor_name,
            trigger_id=trigger_id,
            trigger_type=trigger_type,
            status=trigger_status,
            priority=priority_for_trigger,
            rois=new_rois
        )
        return trigger

    def _compute_trigger_status(
            self, taskor_name: str, trigger_id: str, rois: [List[Roi]],
            mapping_existing_triggers, existing_trigger: bool = False
    ) -> TriggerStatus:
        previous_taskors = self._entrex_graph.previous_in_order_required(taskor_name=taskor_name)
        should_wait_for_optimization = all([roi.optimize_polygon_selection for roi in rois]) and not existing_trigger

        if not previous_taskors:
            return TriggerStatus.WAIT_FOR_OPTIMIZATION if should_wait_for_optimization else TriggerStatus.SKIPPED

        previous_triggers = [mapping_existing_triggers.get((trigger_id, taskor_name)) for taskor_name in previous_taskors]
        previous_triggers = [x for x in previous_triggers if x is not None]

        if len(previous_triggers) < len(previous_taskors):
            return TriggerStatus.WAITING
        else:
            if all(trigger.status == TriggerStatus.COMPLETED for trigger in previous_triggers):
                return TriggerStatus.WAIT_FOR_OPTIMIZATION if should_wait_for_optimization else TriggerStatus.PENDING
            else:
                return TriggerStatus.WAITING

    def optimize_triggers(self, triggers: List[Trigger], use_running_triggers: bool = True):
        sweeps = self._barak_metadata_fetcher.fetch_sweeps(
            sweep_gids=[trigger.get_clean_trigger_id() for trigger in triggers]
        )
        sweep_sensor_group = defaultdict(list)
        for sweep in sweeps:
            sweep_sensor_group[sweep.sensor].append(sweep)

        rois = {roi for trigger in triggers for roi in trigger.roi_ids}

        running_sweeps_sensor_group = defaultdict(list)
        if use_running_triggers:
            running_triggers = self._knowledge_cener.trigger_db_interface.find_ongoing_triggers_by_roi_ids(
                list(rois)
            )
            running_sweeps = self._barak_metadata_fetcher.fetch_sweeps(
                sweep_gids=[running_trigger.trigger_id for running_trigger in running_triggers
                            if not running_trigger.is_mutation()]
            ) if running_triggers else []

            for sweep in running_sweeps:
                if sweep.sensor in sweep_sensor_group:
                    running_sweeps_sensor_group[sweep.sensor].append(sweep)

        for sensor in sweep_sensor_group:
            mandatory_polygon = [
                running_sweep.trace_utm for running_sweep in running_sweeps_sensor_group.get(sensor, [])
            ]

            polygons = [sweep.trace_utm for sweep in sweep_sensor_group[sensor]]
            start = os.times().elapsed
            keep_ids = greedy_sweep_cover(polygons, mandatory_polygon=mandatory_polygon)
            elapsed = os.times().elapsed - start
            logger.info(f"greedy_sweep_cover took {elapsed} sec")
            kept_sweep_ids = {sweeps[i].sweep_gid for i in keep_ids}
            removed = {sweeps[i].sweep_gid for i in range(len(sweeps)) if i not in keep_ids}
            for trigger in triggers:
                if trigger.status == TriggerStatus.WAIT_FOR_OPTIMIZATION:
                    sweep_id = trigger.get_clean_trigger_id()
                    if sweep_id in removed:
                        trigger.status = TriggerStatus.REDUNDANT
                    elif sweep_id in kept_sweep_ids:
                        trigger.status = TriggerStatus.PENDING
            self._knowledge_cener.trigger_db_interface.update_triggers(triggers)
            logger.info(f"Remove {len(removed)} redundant sweeps, keep {len(kept_sweep_ids)} sweeps")

    def manage_live_run_optimization(self) -> None:
        grouped_taskors = self._entrex_graph.get_all_connected_components()
        for taskor_names in grouped_taskors:
            triggers = self._knowledge_cener.trigger_db_interface.find_triggers_waiting_for_optimization(taskor_names)
            triggers = [trigger for trigger in triggers if not trigger.is_mutation()]
            triggers = [trigger for trigger in triggers if all(
                [roi.running_mode == RoiRunningMode.REALTIME for roi in trigger.rois]
            )]

        if len(triggers) >= OPTIMIZATION_MIN_SIZE:
            self.optimize_triggers(triggers)
        elif triggers and min([trigger.update_time for trigger in triggers]) < datetime.now(timezone.utc) - timedelta(
            seconds=OPTIMIZATION_MAX_WAIT_SECONDS
        ):
            logger.info(f"Waited optimization for {OPTIMIZATION_MAX_WAIT_SECONDS} seconds, abort optimization")
            for trigger in triggers:
                trigger.status = TriggerStatus.PENDING
            self._knowledge_cener.trigger_db_interface.update_triggers(triggers)

    def manage_on_demand_optimization(self) -> None:
        on_demand_rois = self._knowledge_cener.roi_db_interface.get_on_demand_rois()
        for on_demand_roi in on_demand_rois:
            triggers = self._knowledge_cener.trigger_db_interface.find_triggers_by_roi_waiting_for_optimization(
                on_demand_roi._id
            )
            triggers = [trigger for trigger in triggers if not trigger.is_mutation()]

            if len(triggers) >= OPTIMIZATION_MIN_SIZE:
                self.optimize_triggers(triggers, use_running_triggers=False)
            elif triggers and min([trigger.update_time for trigger in triggers]) < datetime.now(timezone.utc) - timedelta(
                seconds=OPTIMIZATION_MAX_WAIT_SECONDS
            ):
                logger.info(f"Waited optimization for {OPTIMIZATION_MAX_WAIT_SECONDS} seconds, abort optimization")
                for trigger in triggers:
                    trigger.status = TriggerStatus.PENDING
                self._knowledge_cener.trigger_db_interface.update_triggers(triggers)