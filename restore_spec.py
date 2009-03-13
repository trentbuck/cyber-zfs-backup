#
# A specification for files/directories to include from a
# collection - either tarball or zipfile.
#
# Uses the browse.FileSpec class.

import debug

import datetime

import db
import chroot
import browse
import auth

class BadInclude(Exception):
    def __init__(self, value=""):
        self.value = value
    def __str__(self):
        return self.value


# Tracks paths to include and paths to exclude.
#
# Note: This is actually going to have to autoslurp to/from the
# database - adding and removing will have to update DB too.
# Shit.
#
# Ah, it's not too bad. Don't stress. Remember, you do *not* need to
# worry about performance - take the simplest and crudest option
# available, it'll be fine. Remember ec.cgi!
class RestoreSpec:
    def __init__(self, restore_id=None):
        # Try to grab the current active restore for this user. If
        # there isn't one there, create one.
        ( username, _, company_name, _ ) = auth.login_status()
        self.username = username
        self.company_name = company_name
        if restore_id is None:
            # Either create new or grab existing(!).
            row = db.get1("select id from restores where active and username = %(username)s and company_name = %(company_name)s", vars())
            db.commit()
            if row is None:
                # Create a new one.
                creation = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                db.do("insert into restores ( username, company_name, creation ) values ( %(username)s, %(company_name)s, %(creation)s )", vars())
                row = db.get1("select id from restores where username = %(username)s and company_name = %(company_name)s and creation = %(creation)s", vars())
                db.commit()
            # Grab the id.
            restore_id = int(row[0])

        debug.plog("Setting restore_id to %s..." % ( restore_id ))
        self.restore_id = restore_id

        # Initialise.
        self.include_set = {}
        self.disk_usage_running_total = 0

        self.update_from_db()

    def update_from_db(self):
        debug.plog("Current self.restore_id is %s of type %s." % ( self.restore_id, str(type(self.restore_id)) ))
        restore_id = self.restore_id
        rows = db.get("select s.name, file_path, du_size from restore_files r, shares s where r.share_id = s.id and r.restore_id = %(restore_id)s", vars())
        db.commit()

        for r in rows:
            share = r[0]
            path = r[1]
            du_size = r[2]
            sp = chroot.build_share_path(self.company_name, r[0])
            mychroot = chroot.Chroot(sp)
            chrooted_path = mychroot.chrooted_path(path)
            share_plus_path = browse.join_share_to_path(share, path)
            self.include_set[share_plus_path] = browse.FileSpec(chrooted_path, share, disk_usage=du_size)
        
        self.disk_usage_running_total = sum([ r[2] for r in rows ])

    def __str__(self):
        """ Return a list of the included share+paths. """
        return str([ sp for sp in self.include_set ])

    def is_included(self, file_spec):
        # It has to be both the share and the path.
        if file_spec.share_plus_path in self.include_set:
            return True
        # First make sure the ancestors are actually acquired.
        file_spec.chrooted_path.acquire_ancestors()
        # Now check for ancestors in the include set.
        ancestor_paths = [ browse.join_share_to_path(file_spec.share, cp.path) for cp in file_spec.chrooted_path.ancestors ]
        for ap in ancestor_paths:
            if ap in self.include_set:
                return True
        return False

    def include(self, file_spec):
        debug.plog("Trying to include %s into include_set %s..." % ( file_spec.share_plus_path, self.include_set ))
        # This is a crucial part of the logic.
        if self.is_included(file_spec):
            raise BadInclude("File %s is already included in the restore spec." % ( file_spec.share_plus_path ))
        # We need the disk usage.
        # Just for the insert.
        du_size = file_spec.acquire_disk_usage()
        self.disk_usage_running_total += file_spec.disk_usage
        # Include it.
        self.include_set[file_spec.share_plus_path] = file_spec

        # Update the DB.
        row = db.get1("select id from shares where name = %(share_name)s and company_name = %(company_name)s", { 'company_name' : self.company_name, 'share_name' : file_spec.share })
        if row is None:
            # FIXME: Raise a better exception.
            raise BadInclude("Share %s does not exist in DB." % ( file_spec.share ))
        share_id = row[0]
        restore_id = self.restore_id
        file_path = file_spec.path
        db.do("insert into restore_files ( restore_id, share_id, file_path, du_size ) values ( %(restore_id)s, %(share_id)s, %(file_path)s, %(du_size)s)", vars())
        db.commit()

    def remove(self, file_spec):
        # FIXME: Should check that the restore_id is active
        # before doing anything.
        debug.plog("Trying to remove %s from include_set %s..." % ( file_spec.share_plus_path, self.include_set ))
        # Can only remove paths that are directly included.
        if not file_spec.share_plus_path in self.include_set:
            raise BadInclude("File %s is not directly included in the restore spec." % ( file_spec.share_plus_path ))
        # We need the disk usage.
        file_spec.acquire_disk_usage()
        self.disk_usage_running_total -= file_spec.disk_usage
        # Remove it.
        del self.include_set[file_spec.share_plus_path]

