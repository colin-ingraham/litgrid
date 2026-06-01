from django.contrib import admin
from .models import ConnectionsPuzzle, ConnectionsGroup, ConnectionsBookEntry, ConnectionsDraft, PuzzleCompletion


class ConnectionsBookEntryInline(admin.TabularInline):
    model = ConnectionsBookEntry
    extra = 0
    readonly_fields = ('slot',)
    autocomplete_fields = ('book',)


class ConnectionsGroupInline(admin.StackedInline):
    model = ConnectionsGroup
    extra = 0
    readonly_fields = ('order', 'difficulty')


@admin.register(ConnectionsGroup)
class ConnectionsGroupAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'puzzle', 'difficulty', 'order')
    list_filter  = ('difficulty',)
    inlines      = [ConnectionsBookEntryInline]


@admin.register(ConnectionsPuzzle)
class ConnectionsPuzzleAdmin(admin.ModelAdmin):
    list_display    = ('__str__', 'release_date', 'is_released', 'created_by', 'created_at', 'is_complete')
    list_filter     = ('release_date',)
    list_editable   = ('release_date',)   # edit release date inline in the list view
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    inlines         = [ConnectionsGroupInline]

    def is_complete(self, obj):
        return obj.is_complete()
    is_complete.boolean = True
    is_complete.short_description = 'Complete'

    def is_released(self, obj):
        return obj.is_released
    is_released.boolean = True
    is_released.short_description = 'Live'


@admin.register(ConnectionsDraft)
class ConnectionsDraftAdmin(admin.ModelAdmin):
    list_display    = ('__str__', 'created_by', 'books_placed', 'updated_at')
    readonly_fields = ('created_at', 'updated_at', 'created_by')


@admin.register(PuzzleCompletion)
class PuzzleCompletionAdmin(admin.ModelAdmin):
    list_display  = ('puzzle', 'won', 'mistakes_made', 'completed_at')
    list_filter   = ('won', 'puzzle')
    readonly_fields = ('puzzle', 'session_key', 'won', 'mistakes_made', 'completed_at')