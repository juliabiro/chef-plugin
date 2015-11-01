import sublime
import sublime_plugin
import os
import json


def set_chef_root(path):
    """Locate the root chef directory and save it as a setting.

    Assumption: the chef root is called prezi-chef. Also: UNIX file system.
    Backup, just in case someone cloned the repo to a different name: the chef root has a dir called cookbooks in it.
    """
    settings = sublime.load_settings('Chef-Plugin.sublime-settings')
    if "prezi-chef" in path:
        settings.set('chef_root', path[:path.index("prezi-chef")] + "prezi-chef/")
        return
    else:
        while "/" in path:
            path = path[:path.rfind("/")]
            if os.path.isdir(path + "/cookbooks"):
                settings.set('chef_root', path)
                return
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
    def run(self, edit):
        settings = sublime.load_settings('Chef-Plugin.sublime-settings')
        if settings.get("chef_root", None) is None:
            try:
                set_chef_root(self.view.file_name())
            except:
                sublime.error_message("Can't find chef root!")
                return
        self.chef_root = settings.get("chef_root")
        sels = self.view.sel()
        for s in sels:
            line = self.view.line(s)
            filename = get_resource_path(self.chef_root, self.view.substr(line))
            if filename:
                self.view.window().open_file(filename, sublime.ENCODED_POSITION)


class ExpandRunlistCommand(sublime_plugin.TextCommand):
    """List all recipes that the given role file invokes; walk included roles and recipes recursively."""
    def run(self, edit):
        settings = sublime.load_settings('Chef-Plugin.sublime-settings')
        if settings.get("chef_root", None) is None:
            try:
                set_chef_root(self.view.file_name())
            except:
                sublime.error_message("Can't find chef root!")
                return
        self.chef_root = settings.get("chef_root")

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


class FindAttributeUsagesCommand(ExpandRunlistCommand):
    """Find the recipes that access the attribute under the cursor."""

    def run(self, edit):
        settings = sublime.load_settings('Chef-Plugin.sublime-settings')
        if settings.get("chef_root", None) is None:
            try:
                set_chef_root(self.view.file_name())
            except:
                sublime.error_message("Can't find chef root!")
                return
        self.chef_root = settings.get("chef_root")

        try:
            self.body_string = self.view.substr(sublime.Region(0, self.view.size()))
            self.body_dict = json.loads(self.body_string)
            self.body_list = self.body_string.split("\n")
        except:
            sublime.error_message("Not a json file!")
            return

        self.expanded = self.expand("ROLE", self.body_dict, 0)

        sels = self.view.sel()
        for s in sels:
            attribute = []
            line_index = self.view.rowcol(s.begin())[0]
            indent_level = len(self.body_list[line_index])
            while line_index > 0:
                line = self.body_list[line_index]
                if '"' in line and ":" in line:
                    if line.index('"') < indent_level:
                        indent_level = line.index('"')
                        keyword = line[line.index('"') + 1:line.index('"', line.index('"') + 1)]
                        attribute += [keyword]
                line_index -= 1
            if keyword not in ["normal", "default_attributes", "override_attributes"]:
                continue
            attribute_string = "node" + "".join(["['" + k + "']" for k in reversed(attribute[:-1])])

            # go through all recipes in the expanded list and somehow grep for the attribute
            match_count = file_count = 0
            results = "Searching " + str(self.expanded.count('\n') + 1) + " files for \"" + attribute_string + "\"\n"
            for item in self.expanded.split("\n"):
                if item.strip().startswith("recipe"):
                    file_path = get_resource_path(self.chef_root, item)
                    f = open(file_path)
                    file_contents = f.read()
                    f.close()
                    if attribute_string in file_contents:
                        file_count += 1
                        first_flag = True
                        results += "\n" + item.strip() + "\n" + file_path + ":\n"
                        file_list = file_contents.split('\n')
                        for (i, line) in enumerate(file_list):
                            if attribute_string in line:
                                match_count += 1
                                if first_flag:
                                    first_flag = False
                                else:
                                    results += "    ..\n"
                                results += "\n".join([str(k).rjust(5) + (": " if k == i else "  ") + file_list[k] for k in range(i - 2, i + 3)]) + "\n"
            results += "\n" + str(match_count) + " match" + ("es" if match_count > 1 else "")
            results += " in " + str(file_count) + " file" + ("s" if file_count > 1 else "") + "\n\n\n"
            try:
                self.results = self.view.window().new_file()
                self.results.set_name('Attribute search results')
                self.results.set_syntax_file('Packages/Default/Find Results.hidden-tmLanguage')
                self.results.insert(edit, 0, results)
            except Exception as e:
                sublime.error_message(str(e))
