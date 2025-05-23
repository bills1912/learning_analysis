from django.db import models

class StudentActivityLog(models.Model):
    student_id = models.CharField(max_length=50)
    session_id = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    class Meta:
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['start_time']),
        ]

class CourseActivity(models.Model):
    ACTIVITY_TYPES = [
        ('forum', 'Forum Diskusi'),
        ('task', 'Tugas'),
        ('video', 'Video Pembelajaran'),
        ('quiz', 'Kuis'),
    ]
    
    student_id = models.CharField(max_length=50)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    timestamp = models.DateTimeField()
    duration = models.PositiveIntegerField(help_text="Durasi dalam menit")

class LearningProfile(models.Model):
    student_id = models.CharField(max_length=50, primary_key=True)
    avg_duration = models.FloatField(verbose_name="Rata-rata Durasi Belajar (menit)")
    sessions_per_week = models.FloatField(verbose_name="Sesi per Minggu")
    night_activity_freq = models.FloatField(verbose_name="Frekuensi Aktivitas Malam")
    forum_vs_task = models.FloatField(verbose_name="Rasio Forum vs Tugas")
    learning_type = models.CharField(max_length=20, verbose_name="Tipe Belajar")
    cluster = models.IntegerField(verbose_name="Cluster")
    
    def __str__(self):
        return f"{self.student_id} - {self.learning_type}"
