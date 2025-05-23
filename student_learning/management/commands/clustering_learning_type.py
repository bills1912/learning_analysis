# student_learning/management/commands/cluster_learning_type.py
import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from student_learning.models import StudentActivityLog, CourseActivity, LearningProfile

class Command(BaseCommand):
    help = 'Cluster students into learning types with NaN handling'

    def handle(self, *args, **options):
        try:
            # 1. Ambil data dan hitung fitur
            features = self.calculate_features()
            
            # 2. Handle NaN values
            features_clean = self.handle_nan(features)
            
            # 3. Normalisasi dan clustering
            self.run_clustering(features_clean)
            
            self.stdout.write(self.style.SUCCESS("Clustering selesai!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))

    def calculate_features(self):
        """Hitung fitur dengan penanganan error untuk data kosong."""
        logs = StudentActivityLog.objects.all().values(
            'student_id', 'start_time', 'end_time', 'session_id'
        )
        df = pd.DataFrame.from_records(logs)
        
        if df.empty:
            raise ValueError("Data aktivitas kosong! Pastikan tabel StudentActivityLog terisi.")
        
        # Hitung durasi (dalam menit)
        df['duration'] = (df['end_time'] - df['start_time']).dt.total_seconds() / 60
        
        # Group by student
        features = df.groupby('student_id').apply(
            lambda x: pd.Series({
                'avg_duration': x['duration'].mean(),
                'sessions_per_week': x['session_id'].nunique() / 4,
                'night_activity_freq': self.get_night_freq(x),
                'forum_vs_task': self.get_forum_ratio(x['student_id'].iloc[0])
            })
        ).reset_index()
        
        return features

    def get_night_freq(self, df_group):
        """Hitung frekuensi aktivitas malam (20:00-06:00) dengan penanganan divisi zero."""
        night_mask = (df_group['start_time'].dt.hour >= 20) | (df_group['start_time'].dt.hour <= 6)
        night_count = night_mask.sum()
        total = len(df_group)
        return night_count / total if total > 0 else 0.0

    def get_forum_ratio(self, student_id):
        """Hitung rasio forum/tugas dengan penanganan data kosong."""
        activities = CourseActivity.objects.filter(
            student_id=student_id,
            activity_type__in=['forum', 'task']
        ).values('activity_type')
        
        if not activities:
            return 0.5  # Nilai default jika tidak ada data
        
        df = pd.DataFrame.from_records(activities)
        counts = df['activity_type'].value_counts()
        forum = counts.get('forum', 0)
        task = counts.get('task', 0)
        return forum / (forum + task) if (forum + task) > 0 else 0.5

    def handle_nan(self, df):
        """Ganti NaN dengan nilai median atau default."""
        # Nilai default untuk tiap kolom
        defaults = {
            'avg_duration': df['avg_duration'].median() or 30.0,
            'sessions_per_week': df['sessions_per_week'].median() or 2.0,
            'night_activity_freq': 0.0,
            'forum_vs_task': 0.5
        }
        
        return df.fillna(defaults)

    def run_clustering(self, df):
        """Normalisasi data dan jalankan KMeans."""
        scaler = StandardScaler()
        X = scaler.fit_transform(df[['avg_duration', 'sessions_per_week', 'night_activity_freq', 'forum_vs_task']])
        
        kmeans = KMeans(n_clusters=3, random_state=42)
        df['cluster'] = kmeans.fit_predict(X)
        df['learning_type'] = df['cluster'].map({
            0: 'Intensif',
            1: 'Santai',
            2: 'Pasif'
        })
        
        # Simpan ke database
        for _, row in df.iterrows():
            LearningProfile.objects.update_or_create(
                student_id=row['student_id'],
                defaults={
                    'avg_duration': row['avg_duration'],
                    'sessions_per_week': row['sessions_per_week'],
                    'night_activity_freq': row['night_activity_freq'],
                    'forum_vs_task': row['forum_vs_task'],
                    'learning_type': row['learning_type'],
                    'cluster': row['cluster']
                }
            )