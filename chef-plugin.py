import sublime
import sublime_plugin
import os
import json


def get_chef_root(path):
    """Return the root chef directory for the current file, or None if it can't be found.

    Assumption: the chef root is called prezi-chef. Also: UNIX file system.
    Backup, just in case someone cloned the repo to a different name: the chef root has a dir called cookbooks in it.
    """
    if "prezi-chef" in path:
        return path[:path.index("prezi-chef")] + "prezi-chef/"
    else:
        while "/" in path:
            path = path[:path.rfind("/")]
            if os.path.isdir(path + "/cookbooks"):
                return path
    raise Exception


def get_resource_path(chef_root, resource):
    """Return the absolute path for a recipe or role name."""
    if "recipe" in resource:
        if "include_recipe" in resource:
            quotes = resource[resource.index("include_recipe") + 15]     # can be either " or '
            start = resource.index("include_recipe") + 16
            end = resource.find(quotes, resource.index("include_recipe") + 16)
        else:
            start = resource.index("recipe[") + 7
            end = resource.find("]", resource.index("recipe[") + 7)
        recipe_name = resource[start:end]
        if "::" in recipe_name:
            delimiter = recipe_name.index("::")
            return chef_root + "cookbooks/" + recipe_name[:delimiter] + "/recipes/" + recipe_name[delimiter + 2:] + ".rb"
        else:
            return chef_root + "cookbooks/" + recipe_name + "/recipes/default.rb"
    else:
        start = resource.index("role[") + 5
        end = resource.find("]", resource.index("role[") + 5)
        role_name = resource[start:end]
        return chef_root + "roles/" + role_name + ".json"


class JumpToResourceCommand(sublime_plugin.TextCommand):
    """Pick recipe or role name from chef statements and open the appropriate file."""
    chef_root = None

    def run(self, edit):
        if self.chef_root is None:
            try:
                self.chef_root = get_chef_root(self.view.file_name())
            except:
                sublime.error_message("Can't find chef root!")
                return
        sels = self.view.sel()
        for s in sels:
            line = self.view.line(s)
            filename = get_resource_path(self.chef_root, self.view.substr(line))
            if filename:
                self.view.window().open_file(filename, sublime.ENCODED_POSITION)


class ExpandRunlistCommand(sublime_plugin.TextCommand):
    """List all recipes that the given role file invokes; walk included roles and recipes recursively."""
    chef_root = None

    def run(self, edit):
        if self.chef_root is None:
            try:
                self.chef_root = get_chef_root(self.view.file_name())
            except:
                sublime.error_message("Can't find chef root!")
                return

        try:
            self.body = json.loads(self.view.substr(sublime.Region(0, self.view.size())))
        except:
            sublime.error_message("Not a json file!")
            return

        try:
            self.results = self.view.window().new_file()
            self.results.insert(edit, 0, self.expand("ROLE", self.body, 0))
        except Exception as e:
            sublime.error_message(str(e))

    def expand(self, file_type, file_contents, indent_level):
        """Given the contents of a file as either a dict (role) or string (recipe), print the expanded runlist.

        Assumes that every file is valid - otherwise exceptions will be thrown, so catch them.
        """

        result = ""
        if file_type == "ROLE":
            runlist = file_contents['run_list']
            for item in runlist:
                result += 4 * indent_level * " " + item + "\n"
                if item.startswith('role'):
                    role_name = item[5:-1]
                    role_file = open(self.chef_root + "roles/" + role_name + ".json")
                    role_file_contents = json.loads(role_file.read())
                    role_file.close()
                    result += self.expand("ROLE", role_file_contents, indent_level + 1)
            else:
                recipe_file = open(get_resource_path(self.chef_root, item))
                recipe_file_contents = recipe_file.readlines()
                recipe_file.close()
                result += self.expand("RECIPE", recipe_file_contents, indent_level + 1)
        else:
            for line in file_contents:
                if "include_recipe" in line:
                    # so much for DRY
                    quotes = line[line.index("include_recipe") + 15]     # can be either " or '
                    start = line.index("include_recipe") + 16
                    end = line.find(quotes, line.index("include_recipe") + 16)
                    result += 4 * indent_level * " " + "recipe[" + line[start:end] + "]\n"
                    recipe_file = open(get_resource_path(self.chef_root, line))
                    recipe_file_contents = recipe_file.readlines()
                    recipe_file.close()
                    result += self.expand("RECIPE", recipe_file_contents, indent_level + 1)
        return result

