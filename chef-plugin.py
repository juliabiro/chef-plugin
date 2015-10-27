import sublime
import sublime_plugin
import os

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
        def _does_contain_keyword(view, line, keyword):
            return view.find(keyword, line.begin()) and line.contains(view.find(keyword, line.begin()))

        def _make_recipe_path(recipe_name):
            # if delimeter (::) and recipe name is omitted, it should resolve to ::default
            delim = recipe_name.find("::")
            if delim == -1:
                return self.chef_root + "cookbooks/" + recipe_name + "/recipes/default.rb"
            else:
                return self.chef_root + "cookbooks/" + recipe_name[:delim] + "/recipes/" + recipe_name[delim + 2:] + ".rb"

        def _make_role_path(role_name):
            return self.chef_root + "roles/" + role_name + ".json"

        def _get_target_name(view, line, delim1='\[', delim2='\]'):
            opening = view.find(delim1, line.begin())
            closing = view.find(delim2, opening.begin() + 1)
            return view.substr(sublime.Region(opening.begin() + 1, closing.end() - 1))

        filename = None
        if _does_contain_keyword(self.view, line, "include_recipe"):
            filename = _make_recipe_path(_get_target_name(self.view, line, delim1='\"', delim2='\"'))
        elif _does_contain_keyword(self.view, line, "recipe"):
            filename = _make_recipe_path(_get_target_name(self.view, line))
        elif _does_contain_keyword(self.view, line, "role"):
            filename = _make_role_path(_get_target_name(self.view, line))

        return filename


class BuildRecipeTree(FindRecipeCommand):
    # TODO: first I need a full recipe tree. No way around that
    # 1. find run_list dict, create start set from it
    # 2. create empty recipe tree
    # 3. copy all recipes from start list to recipe tree
    # 4. make a list just from the roles
    # 5. expand roles runlists into a new start list
    # repeat 3-5 until start list is empty

    _recipes_tree = {}
    _attributes_tree = {}
    _all_json = None

    def run(self, edit):
        if not self._validate_chef_root():
            return

        import json
        selection = sublime.Region(0, self.view.size())
        self._all_json = None
        try:
            self._all_json = json.loads(self.view.substr(selection))
        except Exception as e:
            print(e, "not a json file")
            return

        self.build_recipes_tree()
        print("recipes_tree: ", self._recipes_tree)

        self.build_attributes_tree()
        print("attributes_tree: ", self._attributes_tree)

        sels = self.view.sel()
        for s in sels:
            line = _get_attribute_name(self.view.line(s))

            def _get_attribute_name(line):
                opening = view.find('\"', line.begin())
                closing = view.find('\"', opening.begin() + 1)
                return line[opening + 1:closing]

            self.find_attribute_use(_get_attribute_name(line))

    def find_attribute_use(self, attribute):
        # 2. find attribute in tree, make note of path
        # 3. find in recipes
        # 4. return recipe path and location (hehe sounds easy)
        pass

    def build_recipes_tree(self):
        if self._recipes_tree != {} or not self._all_json.has_key("run_list"):
            return

        def _get_name(name):
            s = name.find('[')
            e = name.find(']', s + 1)
            return name[s + 1:e]

        def _copy_recipe_to_tree(RT, recipe_name):
            if recipe_name.find("::") != -1:
                delim = recipe_name.find('::')
                if RT.has_key(recipe_name[:delim]):
                    RT[recipe_name[:delim]].append(recipe_name[delim + 2:])
                else:
                    RT[recipe_name[:delim]] = [recipe_name[delim + 2:]]
            else:
                RT[recipe_name] = ['default']

        def _get_role_runlist(RP, role_name):
            import os
            import json
            role_file = os.path.join(RP, role_name + ".json")

            # read role file
            # find runlist
            try:
                rolefile = open(role_file, "r")
                rl = json.loads(rolefile.read())
                return rl["run_list"]
            except Exception as e:
                print(e)

        runlist = self._all_json["run_list"]
        while runlist != []:
            roles_list = [x for x in runlist if x and x.startswith("role")]
            recipes_list = [x for x in runlist if x and x.startswith("recipe")]

            for recipe in recipes_list:
                _copy_recipe_to_tree(self._recipes_tree, _get_name(recipe))

            runlist = []
            for role in roles_list:
                runlist.extend(_get_role_runlist(self._roles_path, _get_name(role)))

    def build_attributes_tree(self):
        for key in ["normal", "default_attributes", "override_attributes"]:
            if self._all_json.has_key(key):
                if self._attributes_tree.has_key(key):
                    self._attributes_tree[key].update(self._all_json[key])
                else:
                    self._attributes_tree[key] = (self._all_json[key])

# TODO: parse json for default attributes, override_attributes, and for normal tag in nodes
