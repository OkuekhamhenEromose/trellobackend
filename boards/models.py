from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Board(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_boards')
    members = models.ManyToManyField(User, related_name='member_boards', blank=True)
    background_color = models.CharField(max_length=7, default='#0079BF')  # Hex color
    background_image = models.ImageField(upload_to='board_backgrounds/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class List(models.Model):
    title = models.CharField(max_length=255)
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='lists')
    position = models.PositiveIntegerField(default=0)  # For ordering lists
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position']
        unique_together = ['board', 'position']

    def __str__(self):
        return f"{self.title} (Board: {self.board.title})"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.position:
            # Auto-assign position if not provided
            max_position = List.objects.filter(board=self.board).aggregate(
                models.Max('position')
            )['position__max'] or -1
            self.position = max_position + 1
        super().save(*args, **kwargs)


class Card(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    list = models.ForeignKey(List, on_delete=models.CASCADE, related_name='cards')
    position = models.PositiveIntegerField(default=0)  # For ordering cards within a list
    due_date = models.DateTimeField(null=True, blank=True)
    labels = models.JSONField(default=list)  # FIXED: Use list instead of []
    members = models.ManyToManyField(User, related_name='assigned_cards', blank=True)
    attachments = models.JSONField(default=list)  # FIXED: Use list instead of []
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)

    class Meta:
        ordering = ['position']
        unique_together = ['list', 'position']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self._state.adding and not self.position:
            # Auto-assign position if not provided
            max_position = Card.objects.filter(list=self.list).aggregate(
                models.Max('position')
            )['position__max'] or -1
            self.position = max_position + 1
        super().save(*args, **kwargs)


class Comment(models.Model):
    text = models.TextField()
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username if self.author else 'Deleted User'}"


class Checklist(models.Model):
    title = models.CharField(max_length=255, default="Checklist")
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='checklists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.title} (Card: {self.card.title})"


class ChecklistItem(models.Model):
    text = models.CharField(max_length=255)
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE, related_name='items')
    completed = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"{self.text} - {'✓' if self.completed else '✗'}"


class Activity(models.Model):
    ACTIVITY_TYPES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('MOVE', 'Move'),
        ('COMMENT', 'Comment'),
        ('COMPLETE', 'Complete'),
    ]
    
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField()
    data = models.JSONField(default=dict)  # FIXED: Use dict instead of {}
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Activities'

    def __str__(self):
        return f"{self.activity_type} by {self.user.username if self.user else 'Unknown'}"