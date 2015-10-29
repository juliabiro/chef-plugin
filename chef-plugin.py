import sublime
import sublime_plugin
import os
import json

def get_chef_root(path):
    """Return the root chef directory for the current file, or None if it can't be found.

    Assumption: the chef root is called prezi-chef.
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


class JumpToTargetCommand(sublime_plugin.TextCommand):
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
            filename = self.get_target_path_from_line(line)
            if filename:
                self.view.window().open_file(filename, sublime.ENCODED_POSITION)


    def get_target_path_from_line(self, line):
        def does_contain_keyword(view, line, keyword):
            return view.find(keyword, line.begin()) and line.contains(view.find(keyword, line.begin()))

        def make_recipe_path(recipe_name):
            # if delimeter (::) and recipe name is omitted, it should resolve to ::default
            delim = recipe_name.find("::")
            if delim == -1:
                return self.chef_root + "cookbooks/" + recipe_name + "/recipes/default.rb"
            else:
                return self.chef_root + "cookbooks/" + recipe_name[:delim] + "/recipes/" + recipe_name[delim + 2:] + ".rb"

        def make_role_path(role_name):
            return self.chef_root + "roles/" + role_name + ".json"

        def get_target_name(view, line, delim1='\[', delim2='\]'):
            opening = view.find(delim1, line.begin())
            closing = view.find(delim2, opening.begin() + 1)
            return view.substr(sublime.Region(opening.begin() + 1, closing.end() - 1))

        filename = None
        if does_contain_keyword(self.view, line, "include_recipe"):
            filename = make_recipe_path(get_target_name(self.view, line, delim1='\"', delim2='\"'))
        elif does_contain_keyword(self.view, line, "recipe"):
            filename = make_recipe_path(get_target_name(self.view, line))
        elif does_contain_keyword(self.view, line, "role"):
            filename = make_role_path(get_target_name(self.view, line))

        return filename


class ExpandRunlistCommand(sublime_plugin.TextCommand):
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
            self.expand_runlist(self.body, 0)
        except Exception as e:
            sublime.error_message(str(e))

    def expand_runlist(self, file_contents, indent_level):
        runlist = file_contents['run_list']
        for item in runlist:
            if item.startswith('role'):
                role_name = item[5:-1]
                print 4 * indent_level * " " +  item + " ==>"
                role_file = open(self.chef_root + "roles/" + role_name + ".json")
                role_file_contents = json.loads(role_file.read())
                self.expand_runlist(role_file_contents, indent_level + 1)
            else:
                print indent_level * " " +  item
