from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from .forms import EntryForm, TopicForm
from .models import Entry, Topic


def index(request):
    """Общедоступная домашняя страница."""
    return render(request, 'learning_logs/index.html')


@login_required
def topics(request):
    """Пользователь видит только свои темы, от старых к новым."""
    topics = Topic.objects.filter(owner=request.user).order_by('date_added', 'id')
    return render(request, 'learning_logs/topics.html', {'topics': topics})


@login_required
def topic(request, topic_id):
    """Чужая и несуществующая тема одинаково возвращают 404."""
    topic = get_object_or_404(Topic, id=topic_id, owner=request.user)
    entries = topic.entry_set.order_by('-date_added', '-id')
    return render(request, 'learning_logs/topic.html', {'topic': topic, 'entries': entries})


@login_required
@require_http_methods(['GET', 'POST'])
def new_topic(request):
    form = TopicForm(data=request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        topic = form.save(commit=False)
        topic.owner = request.user
        topic.save()
        return redirect('learning_logs:topics')
    return render(request, 'learning_logs/new_topic.html', {'form': form})


@login_required
@require_http_methods(['GET', 'POST'])
def new_entry(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, owner=request.user)
    form = EntryForm(data=request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        entry = form.save(commit=False)
        entry.topic = topic
        entry.save()
        return redirect('learning_logs:topic', topic_id=topic.id)
    return render(request, 'learning_logs/new_entry.html', {'topic': topic, 'form': form})


@login_required
@require_http_methods(['GET', 'POST'])
def edit_entry(request, entry_id):
    entry = get_object_or_404(Entry.objects.select_related('topic'), id=entry_id, topic__owner=request.user)
    form = EntryForm(instance=entry, data=request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('learning_logs:topic', topic_id=entry.topic_id)
    return render(request, 'learning_logs/edit_entry.html', {'entry': entry, 'topic': entry.topic, 'form': form})
