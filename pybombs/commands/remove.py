#
# Copyright 2015 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#
""" PyBOMBS command: install """

import os
import shutil
from pybombs.commands import CommandBase
from pybombs import package_manager
from pybombs import recipe

class Remove(CommandBase):
    """ Remove a package from this prefix """
    cmds = {
        'remove': 'Remove listed packages',
    }

    @staticmethod
    def setup_subparser(parser, cmd=None):
        """
        Set up a subparser for 'remove'
        """
        parser.add_argument(
                'packages',
                help="List of packages to remove",
                action='append',
                default=[],
                nargs='*'
        )
        parser.add_argument(
                '-d', '--no-deps',
                help="Do not remove dependees. May leave prefix in unusable state.",
                action='store_true',
        )

    def __init__(self, cmd, args):
        CommandBase.__init__(self,
                cmd, args,
                load_recipes=False,
                require_prefix=True,
                require_inventory=True,
        )
        self.args.packages = args.packages[0]
        if len(self.args.packages) == 0:
            self.log.error("No packages specified.")
            exit(1)
        # Do not allow any non-source packagers for this:
        self.cfg.set('packagers', '')
        self.pm = package_manager.PackageManager()
        if not self.args.no_deps:
            self.args.packages = self.get_dependees(self.args.packages)

    def run(self):
        """ Go, go, go! """
        ### Sanity checks
        for pkg in self.args.packages:
            if not self.pm.installed(pkg):
                self.log.error("Package {0} is not installed. Aborting.".format(pkg))
                exit(1)
        ### Remove packages
        for pkg in self.args.packages:
            self.log.info("Removing package {0}.".format(pkg))
            # Uninstall:
            self.log.debug("Uninstalling.")
            if not self.pm.uninstall(pkg):
                self.log.warn("Could not uninstall {0} from prefix.".format(pkg))
            # Remove source dir:
            pkg_src_dir = os.path.join(self.prefix.src_dir, pkg)
            self.log.debug("Removing directory {0}.".format(pkg_src_dir))
            shutil.rmtree(pkg_src_dir)
            # Remove entry from inventory:
            self.log.debug("Removing package from inventory.")
            self.inventory.remove(pkg)
            self.inventory.save()

    def get_dependees(self, pkgs):
        """
        From a list of pkgs, return a list that also includes packages
        which depend on them.
        """
        self.log.debug("Resolving dependency list for clean removal.")
        other_installed_pkgs = [x for x in self.inventory.get_packages() if not x in pkgs]
        new_pkgs = []
        for other_installed_pkg in other_installed_pkgs:
            self.log.obnoxious("Checking if {0} is a dependee...".format(other_installed_pkg))
            deps = recipe.get_recipe(other_installed_pkg).get_local_package_data()['depends'] or []
            for pkg in pkgs:
                if pkg in deps:
                    self.log.obnoxious("Yup, it is.")
                    new_pkgs.append(other_installed_pkg)
                    break
        if len(new_pkgs) > 0:
            pkgs = pkgs + new_pkgs
            return self.get_dependees(pkgs)
        return pkgs
