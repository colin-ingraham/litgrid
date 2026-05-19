from django.contrib import admin
from .models import ConnectionsPuzzle, ConnectionsGroup, ConnectionsBookEntry


class ConnectionsBookEntryInline(admin.TabularInline):
    model = ConnectionsBookEntry
    extra = 0
    readonly_fields = ('slot',)
    autocomplete_fields = ('book',)


class ConnectionsGroupInline(admin.StackedInline):
    model = ConnectionsGroup
    extra = 0
    readonly_fields = ('order', 'difficulty')
    inlines = [ConnectionsBookEntryInline]


@admin.register(ConnectionsGroup)
class ConnectionsGroupAdmin(admin.ModelAdmin):
    list_display  = ('__str__', 'puzzle', 'difficulty', 'order')
    list_filter   = ('difficulty',)
    inlines       = [ConnectionsBookEntryInline]


@admin.register(ConnectionsPuzzle)
class ConnectionsPuzzleAdmin(admin.ModelAdmin):
    list_display   = ('__str__', 'created_by', 'created_at', 'is_complete')
    list_filter    = ('created_by',)
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    inlines        = [ConnectionsGroupInline]

    def is_complete(self, obj):
        return obj.is_complete()
    is_complete.boolean = True
    is_complete.short_description = 'Complete'