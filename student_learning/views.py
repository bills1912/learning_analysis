from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Count
from .models import LearningProfile, StudentActivityLog, CourseActivity
import pandas as pd
import plotly.express as px
from plotly.offline import plot

def learning_type_dashboard(request):
    # Ambil parameter filter dari URL
    learning_type_filter = request.GET.get('type', None)
    student_query = request.GET.get('student', None)
    
    # Query data dengan filter jika ada
    if learning_type_filter:
        profiles = LearningProfile.objects.filter(learning_type=learning_type_filter).order_by('student_id')
        student_activity = StudentActivityLog.objects.filter(learning_type=learning_type_filter).order_by('student_id')
        course = CourseActivity.objects.filter(learning_type=learning_type_filter).order_by('student_id')
    else:
        profiles = LearningProfile.objects.all().order_by('student_id')
        student_activity = StudentActivityLog.objects.all().order_by('student_id')
        course = CourseActivity.objects.all().order_by('student_id')
        
    
    # Data untuk dropdown
    student_list = LearningProfile.objects.all().values_list('student_id', flat=True)
    
    # Visualisasi detail mahasiswa terpilih
    selected_student = request.GET.get('student_id', student_list[0] if student_list else None)
    student_data = None
    
    if selected_student:
        student_data = LearningProfile.objects.filter(student_id=selected_student).first()
        
        if student_data:
            # Siapkan data untuk barchart
            metrics = {
                'Durasi Rata-rata (menit)': student_data.avg_duration,
                'Sesi per Minggu': student_data.sessions_per_week,
                'Frekuensi Malam': student_data.night_activity_freq * 100,  # Konversi ke persen
                'Rasio Forum/Tugas': student_data.forum_vs_task * 100
            }
            
            student_chart = px.bar(
                x=list(metrics.keys()),
                y=list(metrics.values()),
                title=f"Profil Belajar - {selected_student}",
                labels={'x': 'Metrik', 'y': 'Nilai'},
                color=list(metrics.keys()),
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            student_chart.update_layout(showlegend=False)
            student_viz = plot(student_chart, output_type='div')
    
    # Setup pagination
    paginator = Paginator(profiles, 10)  # 10 item per halaman
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Hitung total untuk setiap tipe belajar
    type_counts = LearningProfile.objects.values('learning_type').annotate(total=Count('learning_type'))
    
    # Buat DataFrame untuk visualisasi
    data = {
        'student_id': [p.student_id for p in profiles],
        'learning_type': [p.learning_type for p in profiles],
        'avg_duration': [p.avg_duration for p in profiles],
        'sessions_per_week': [p.sessions_per_week for p in profiles],
        'night_activity': [p.night_activity_freq for p in profiles]
    }
    df = pd.DataFrame(data)
    
    # 1. Chart distribusi tipe belajar
    type_chart = px.bar(
        type_counts,
        x='learning_type',
        y='total',
        title='Distribusi Tipe Belajar Mahasiswa',
        color='learning_type',
        color_discrete_map={
            'Intensif': '#1f77b4',
            'Santai': '#ff7f0e',
            'Pasif': '#2ca02c'
        }
    )
    type_chart.update_layout(showlegend=False)
    type_chart = plot(type_chart, output_type='div')
    
    
    heatmap_data = {
        'start_time': [s.start_time for s in student_activity],
        'duration': [c.duration for c in course],
        'learning_type': [p.learning_type for p in profiles],
    }
    heatmap_df = pd.DataFrame(heatmap_data)
    # Buat heatmap jam belajar
    heatmap_fig = px.density_heatmap(
        heatmap_df,
        x=heatmap_df['start_time'].dt.hour,  # Jam dalam sehari
        y=heatmap_df['start_time'].dt.dayofweek,  # Hari dalam seminggu (0=Senin)
        z=heatmap_df['duration'],
        histfunc="avg",
        title="Pola Aktivitas Belajar per Jam & Hari",
        labels={'x': 'Jam', 'y': 'Hari', 'z': 'Durasi Rata-rata (menit)'},
        facet_col="learning_type"
    )
    new_titles = ["Santai", "Intens", "Pasif"]

    for i, annotation in enumerate(heatmap_fig.layout.annotations):
        annotation.text = new_titles[i]
    heatmap_fig.update_yaxes(categoryorder='array', 
                           categoryarray=['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu'])
    
    heatmap_fig.update_layout(
        updatemenus=[
            dict(
                buttons=list([
                    dict(label="Semua Tipe",
                        method="update",
                        args=[{"visible": [True, True, True]}]),
                    dict(label="Intensif",
                        method="update",
                        args=[{"visible": [True, False, False]}])
                ]),
                direction="down",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.1, y=1.1
            )
        ],
    )
    
    heatmap_fig.update_xaxes(
        showticklabels=False,  # Menghilangkan label
        showline=False,       # Menghilangkan garis axis
        ticks="",            # Menghilangkan ticks
    )
    heatmap = plot(heatmap_fig, output_type='div')
    
    context = {
        'type_chart': type_chart,
        # 'scatter_chart': scatter_chart,
        'heatmap': heatmap,
        'page_obj': page_obj,
        'profiles': profiles,
        'total_students': len(profiles),
        'current_filter': learning_type_filter,
        'type_counts': {t['learning_type']: t['total'] for t in type_counts},
        'student_list': student_list,
        'selected_student': selected_student,
        'student_viz': student_viz if selected_student else None,
        'student_data': student_data
    }
    
    return render(request, 'student_learning/dashboard.html', context)