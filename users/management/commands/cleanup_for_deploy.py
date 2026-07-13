"""
Prepare the database for production deploy by wiping all demo/seed data.

By default:
    - KEEPS: superuser accounts, ratings.Facility, ratings.RatingQuestion,
             schema, migrations.
    - WIPES: all non-superuser accounts, sports (teams/matches/competitions),
             attendance, evaluations, events, news, notifications,
             quiz (bank + progress + streaks), dailychallenge (content + progress),
             ratings.Submission + ratings.Answer, activity log,
             and the media/ folder.

Flags:
    --keep-users        Keep every user (do NOT delete non-superusers).
    --wipe-ratings      Also delete ratings.Facility + RatingQuestion.
    --keep-media        Do NOT delete files under media/.
    --dry-run           Show what would be deleted, change nothing.

Examples:
    python manage.py cleanup_for_deploy --dry-run
    python manage.py cleanup_for_deploy
    python manage.py cleanup_for_deploy --wipe-ratings --keep-users
"""
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Wipe demo/seed data and get the database ready for production.'

    def add_arguments(self, parser):
        parser.add_argument('--keep-users', action='store_true')
        parser.add_argument('--wipe-ratings', action='store_true')
        parser.add_argument('--keep-media', action='store_true')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--yes', action='store_true',
                            help='Skip the confirmation prompt.')

    def _count(self, qs):
        try:
            return qs.count()
        except Exception:
            return '?'

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        keep_users = opts['keep_users']
        wipe_ratings = opts['wipe_ratings']
        keep_media = opts['keep_media']

        # ── Import models lazily so the command works even if some apps
        #    are absent (e.g., during CI). ────────────────────────────────
        from users.models import User, ActivityLog
        from attendance.models import AttendanceSession, AttendanceRecord
        from evaluations.models import Evaluation
        from sports.models import (
            Team, CoachAssignment, Competition, Match, GoalRecord, TrainingSchedule,
        )
        from events.models import Event, ParentActivity
        from news.models import NewsPost
        from notifications.models import Notification
        from quiz.models import BibleQuestion, DailyQuizAttempt, UserStreak
        from dailychallenge.models import (
            DailyContent, Question as DcQuestion, Choice as DcChoice,
            ChallengeProgress, ChallengeAnswer,
        )
        from ratings.models import Facility, RatingQuestion, Submission, Answer

        # Preview counts
        summary = []
        summary.append(('quiz.BibleQuestion', BibleQuestion.objects.all()))
        summary.append(('quiz.DailyQuizAttempt', DailyQuizAttempt.objects.all()))
        summary.append(('quiz.UserStreak', UserStreak.objects.all()))
        summary.append(('dailychallenge.ChallengeAnswer', ChallengeAnswer.objects.all()))
        summary.append(('dailychallenge.ChallengeProgress', ChallengeProgress.objects.all()))
        summary.append(('dailychallenge.Choice', DcChoice.objects.all()))
        summary.append(('dailychallenge.Question', DcQuestion.objects.all()))
        summary.append(('dailychallenge.DailyContent', DailyContent.objects.all()))
        summary.append(('ratings.Answer', Answer.objects.all()))
        summary.append(('ratings.Submission', Submission.objects.all()))
        if wipe_ratings:
            summary.append(('ratings.RatingQuestion', RatingQuestion.objects.all()))
            summary.append(('ratings.Facility', Facility.objects.all()))
        summary.append(('notifications.Notification', Notification.objects.all()))
        summary.append(('news.NewsPost', NewsPost.objects.all()))
        summary.append(('events.ParentActivity', ParentActivity.objects.all()))
        summary.append(('events.Event', Event.objects.all()))
        summary.append(('evaluations.Evaluation', Evaluation.objects.all()))
        summary.append(('attendance.AttendanceRecord', AttendanceRecord.objects.all()))
        summary.append(('attendance.AttendanceSession', AttendanceSession.objects.all()))
        summary.append(('sports.GoalRecord', GoalRecord.objects.all()))
        summary.append(('sports.Match', Match.objects.all()))
        summary.append(('sports.TrainingSchedule', TrainingSchedule.objects.all()))
        summary.append(('sports.CoachAssignment', CoachAssignment.objects.all()))
        summary.append(('sports.Competition', Competition.objects.all()))
        summary.append(('sports.Team', Team.objects.all()))
        summary.append(('users.ActivityLog', ActivityLog.objects.all()))
        if not keep_users:
            summary.append((
                'users.User (non-superuser)',
                User.objects.filter(is_superuser=False),
            ))

        self.stdout.write(self.style.NOTICE(
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        ))
        self.stdout.write(self.style.NOTICE('  CLEANUP FOR DEPLOY — PREVIEW'))
        self.stdout.write(self.style.NOTICE(
            '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        ))
        for label, qs in summary:
            self.stdout.write(f'  {self._count(qs):>8}  ×  {label}')

        # Superuser preservation notice
        keep_supers = User.objects.filter(is_superuser=True)
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'  Superusers to keep: {keep_supers.count()} '
            f'({", ".join(u.username for u in keep_supers[:5])}'
            f'{" ..." if keep_supers.count() > 5 else ""})'
        ))
        if not wipe_ratings:
            self.stdout.write(self.style.SUCCESS(
                f'  Rating facilities to keep: {Facility.objects.count()} '
                f'(with {RatingQuestion.objects.count()} questions)'
            ))
        if keep_users:
            self.stdout.write(self.style.SUCCESS(
                f'  All users kept (including {User.objects.filter(is_superuser=False).count()} non-superusers).'
            ))

        # Media folder
        media_root = Path(settings.MEDIA_ROOT)
        media_targets = []
        if not keep_media and media_root.exists():
            for entry in media_root.iterdir():
                if entry.name in ('.gitkeep', '.gitignore'):
                    continue
                media_targets.append(entry)
        if media_targets:
            self.stdout.write('')
            self.stdout.write(self.style.NOTICE(
                f'  Media to remove ({len(media_targets)} entries under {media_root}):'
            ))
            for t in media_targets:
                self.stdout.write(f'    - {t.name}')

        if dry:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUN — nothing was deleted.'))
            return

        if not opts['yes']:
            self.stdout.write('')
            answer = input('Proceed with deletion? Type "yes" to confirm: ').strip().lower()
            if answer != 'yes':
                self.stdout.write(self.style.ERROR('Aborted.'))
                return

        # ── Actual deletion in a transaction ────────────────────────────
        with transaction.atomic():
            for label, qs in summary:
                deleted, _ = qs.delete()
                self.stdout.write(f'  deleted {deleted:>6}  ×  {label}')

        # ── Media cleanup ────────────────────────────────────────────────
        if media_targets:
            for t in media_targets:
                try:
                    if t.is_dir():
                        shutil.rmtree(t)
                    else:
                        t.unlink()
                    self.stdout.write(f'  removed media/{t.name}')
                except Exception as e:
                    self.stderr.write(f'  ! could not remove {t}: {e}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Done — database is ready for deploy.'))
        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('  1. Verify with:  python manage.py shell -c '
                          '"from users.models import User; print(User.objects.count())"')
        if wipe_ratings:
            self.stdout.write('  2. Re-seed ratings if needed:  python manage.py seed_ratings --activate')
        self.stdout.write('  3. Commit your code, deploy, run migrate on the server, createsuperuser.')
