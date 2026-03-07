from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import TimelineExhibit
from .tasks import reconstruct_timeline_events


@receiver(post_save, sender=TimelineExhibit)
def handle_timeline_exhibit_save(sender, instance, created, **kwargs):
    if created:
        return

    timeline_exhibit: TimelineExhibit = instance
    timeline = timeline_exhibit.timeline

    total_exhibits = TimelineExhibit.objects.filter(timeline_id=timeline.id).count()
    completed_exhibits = TimelineExhibit.objects.filter(
        timeline_id=timeline.id,
        event_extraction_status=TimelineExhibit.Status.COMPLETED,
    ).count()
    failed_exhibits = TimelineExhibit.objects.filter(
        timeline_id=timeline.id,
        event_extraction_status=TimelineExhibit.Status.FAILED,
    ).count()

    if failed_exhibits > 0:
        # If any exhibit has failed, mark the timeline as failed and do not proceed to PASS-2
        timeline.mark_as_failed()
        return

    if total_exhibits == completed_exhibits:
        # fan-out fan-in architecture:
        # only proceed to reconstruct timeline events (PASS-2) after
        # all exhibits have been processed and completed successfully
        reconstruct_timeline_events.delay(timeline.id)
