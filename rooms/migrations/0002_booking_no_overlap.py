from django.db import migrations

# Half-open range: a stay occupies [check_in, check_out). btree_gist supplies
# the equality operator for room_id on a GiST index.
ADD_EXCLUSION = """
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE rooms_booking
    ADD CONSTRAINT booking_no_overlap
    EXCLUDE USING gist (
        room_id WITH =,
        tstzrange(check_in, check_out, '[)') WITH &&
    );
"""

DROP_EXCLUSION = """
ALTER TABLE rooms_booking DROP CONSTRAINT IF EXISTS booking_no_overlap;
"""


class PostgresOnlyRunSQL(migrations.RunSQL):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return
        super().database_backwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):
    dependencies = [
        ("rooms", "0001_initial"),
    ]

    operations = [
        PostgresOnlyRunSQL(sql=ADD_EXCLUSION, reverse_sql=DROP_EXCLUSION),
    ]
