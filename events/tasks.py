import logging

from celery import shared_task
from openai import OpenAIError

from .models import Timeline, TimelineExhibit
from .services import CandidateEventExtractor, TimelineEventReconstructor

logger = logging.getLogger(__name__)


@shared_task
def start_timeline_processing(timeline_id: int) -> None:
    """
    Start the processing of a timeline by extracting candidate events and reconstructing timeline events (fan-out fan-in architecture).
    This function is called when a timeline is created and needs to be processed.
    """
    try:
        timeline = Timeline.objects.get(id=timeline_id)
    except Timeline.DoesNotExist:
        logger.error(f"Timeline with id {timeline_id} does not exist.")
        return

    timeline.mark_as_processing()

    exhibits = TimelineExhibit.objects.filter(timeline_id=timeline_id).values_list(
        "id", flat=True
    )
    for exhibit_id in exhibits:
        extract_candidate_events.delay(exhibit_id)


@shared_task
def extract_candidate_events(timeline_exhibit_id: int) -> None:
    """
    Extract candidate events from the timeline exhibit.
    This task is called when a timeline exhibit is created and needs to have candidate events extracted.
    """
    try:
        timeline_exhibit = TimelineExhibit.objects.get(id=timeline_exhibit_id)
    except TimelineExhibit.DoesNotExist:
        logger.error(f"TimelineExhibit with id {timeline_exhibit_id} does not exist.")
        return

    timeline_exhibit.mark_as_processing()

    try:
        extractor = CandidateEventExtractor(timeline_exhibit=timeline_exhibit)
        candidate_events = extractor.run()
    except (OpenAIError, ValueError) as e:
        logger.error(
            f"Error extracting candidate events for TimelineExhibit id {timeline_exhibit_id}: {str(e)}"
        )
        timeline_exhibit.mark_as_failed()
        return

    timeline_exhibit.mark_as_completed()

    logger.info(
        f"Extracted and saved {len(candidate_events)} candidate events for TimelineExhibit id {timeline_exhibit_id}."
    )


@shared_task
def reconstruct_timeline_events(timeline_id: int) -> None:
    """
    Reconstruct timeline events from candidate events.
    This task is called when candidate events have been extracted and need to be reconstructed into timeline events.
    """
    try:
        timeline = Timeline.objects.get(id=timeline_id)
    except Timeline.DoesNotExist:
        logger.error(f"Timeline with id {timeline_id} does not exist.")
        return

    try:
        reconstructor = TimelineEventReconstructor(timeline=timeline)
        timeline_events = reconstructor.run()
    except (OpenAIError, ValueError) as e:
        logger.error(
            f"Error reconstructing timeline events for Timeline id {timeline_id}: {str(e)}"
        )
        timeline.mark_as_failed()
        return

    timeline.mark_as_completed()

    logger.info(
        f"Reconstructed and saved {len(timeline_events)} timeline events for Timeline id {timeline_id}."
    )
