"""
Seed a sample Daily Challenge for today (idempotent).

Usage:
    python manage.py seed_daily_challenge
    python manage.py seed_daily_challenge --date 2026-05-26
"""
from datetime import date, datetime

from django.core.management.base import BaseCommand
from dailychallenge.models import DailyContent, Question, Choice


# (question_text, [choices], correct_index)
SAMPLE = {
    'reference': 'يوحنا 15:1-8',
    'questions': [
        ('من هو النبي الذي ابتلعه الحوت؟',
         ['موسى', 'يونان', 'داود', 'يوسف'], 1),
        ('من بنى الفلك ليخلص من الطوفان؟',
         ['إبراهيم', 'موسى', 'نوح', 'سليمان'], 2),
        ('في أي مدينة وُلد السيد المسيح؟',
         ['الناصرة', 'بيت لحم', 'أورشليم', 'كفرناحوم'], 1),
    ],
}


class Command(BaseCommand):
    help = 'Seeds a sample Daily Challenge for today (or a given --date).'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, default=None,
                            help='YYYY-MM-DD (defaults to today)')

    def handle(self, *args, **options):
        if options['date']:
            target = datetime.strptime(options['date'], '%Y-%m-%d').date()
        else:
            target = date.today()

        content, created = DailyContent.objects.get_or_create(
            date=target,
            defaults={'bible_reference': SAMPLE['reference'], 'is_published': True},
        )
        if not created and content.questions.exists():
            self.stdout.write(self.style.WARNING(
                f'Daily content for {target} already exists with questions — skipping.'
            ))
            return

        for order, (text, choices, correct_idx) in enumerate(SAMPLE['questions'], 1):
            q = Question.objects.create(daily_content=content, text=text, order=order)
            for i, ctext in enumerate(choices):
                Choice.objects.create(
                    question=q, text=ctext, is_correct=(i == correct_idx),
                )

        self.stdout.write(self.style.SUCCESS(
            f'Seeded Daily Challenge for {target}: {content.questions.count()} questions.'
        ))
