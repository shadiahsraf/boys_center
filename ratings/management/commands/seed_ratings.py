"""
Seed the 7 default facilities + their Arabic rating questions.

Idempotent — safe to run repeatedly. If a facility with the same name already
exists, it is updated and its questions are reset to the canonical list.

Usage:  python manage.py seed_ratings
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from ratings.models import Facility, RatingQuestion


SEED = [
    {
        'name': 'حمام السباحة',
        'icon': '🏊',
        'description': 'تقييم خدمة حمام السباحة',
        'questions': [
            'نظافة مياه حمام السباحة',
            'نظافة دورات المياه',
            'مستوى الأمان والإشراف داخل حمام السباحة',
            'جودة التدريب (للمشتركين بالتدريبات)',
            'تعامل المدربين والمشرفين',
        ],
    },
    {
        'name': 'القاعات',
        'icon': '🏛️',
        'description': 'تقييم خدمة القاعات',
        'questions': [
            'نظافة القاعة',
            'كفاءة التكييف والتهوية',
            'تعامل مسئولي الحجز والعمال',
        ],
    },
    {
        'name': 'بيت المؤتمرات',
        'icon': '🏨',
        'description': 'تقييم خدمة بيت المؤتمرات',
        'questions': [
            'نظافة الغرف',
            'جودة الأثاث والمفروشات',
            'جودة التكييف',
            'سرعة الاستجابة لأي طلبات أو شكاوى',
        ],
    },
    {
        'name': 'النشاط الرياضي',
        'icon': '⚽',
        'description': 'تقييم النشاط الرياضي',
        'questions': [
            'جودة الملاعب',
            'جودة التدريب',
            'كفاءة المدربين',
            'تعامل المشرفين',
            'نظافة الملاعب والحمامات والطرق',
            'جودة حديقة الأطفال والمشرفات',
        ],
    },
    {
        'name': 'الرحلات والملاعب',
        'icon': '🚌',
        'description': 'تقييم الرحلات والملاعب',
        'questions': [
            'جودة الملاعب',
            'نظافة الأماكن المحيطة ومناطق الانتظار',
            'تنظيم الرحلة أو الزيارة',
            'تعامل مسئولي الحجز',
            'تعامل المشرفين',
        ],
    },
    {
        'name': 'المطعم',
        'icon': '🍽️',
        'description': 'تقييم خدمة المطعم',
        'questions': [
            'جودة الطعام',
            'مذاق الطعام',
            'تنوع الأصناف',
            'نظافة المطعم',
        ],
    },
    {
        'name': 'الكانتين',
        'icon': '🥤',
        'description': 'تقييم خدمة الكانتين',
        'questions': [
            'تنوع المنتجات',
            'توافر المنتجات المطلوبة',
            'جودة المشروبات',
            'جودة المنتجات المقدمة',
            'سرعة الخدمة',
            'نظافة الكانتين',
            'الأسعار',
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed the 7 default facilities and their Arabic rating questions.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--activate', action='store_true',
            help='Open all facilities for rating immediately.',
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        activate = opts.get('activate', False)
        created = 0
        updated = 0
        for order, spec in enumerate(SEED):
            facility, was_created = Facility.objects.get_or_create(
                name=spec['name'],
                defaults={
                    'icon': spec['icon'],
                    'description': spec['description'],
                    'order': order,
                    'is_active': activate,
                },
            )
            if not was_created:
                facility.icon = spec['icon']
                facility.description = spec['description']
                facility.order = order
                if activate:
                    facility.is_active = True
                facility.save()
                updated += 1
            else:
                created += 1

            # Reset questions to canonical list (idempotent)
            facility.questions.all().delete()
            for q_order, text in enumerate(spec['questions']):
                RatingQuestion.objects.create(
                    facility=facility, text=text, order=q_order,
                )

        try:
            self.stdout.write(self.style.SUCCESS(
                f'Done — {created} created, {updated} updated. '
                f'{Facility.objects.count()} total facilities, '
                f'{RatingQuestion.objects.count()} total questions.'
            ))
            if activate:
                self.stdout.write(self.style.SUCCESS(
                    'All facilities are now OPEN for rating.'
                ))
            else:
                self.stdout.write(
                    'Facilities are CLOSED. Open them from /rate/manage/ or '
                    'pass --activate.'
                )
        except UnicodeEncodeError:
            # Windows console may not be UTF-8
            self.stdout.write(
                f'Done — created={created} updated={updated} '
                f'facilities={Facility.objects.count()} '
                f'questions={RatingQuestion.objects.count()}'
            )
