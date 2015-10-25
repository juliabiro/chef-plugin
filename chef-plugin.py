import sublime, sublime_plugin

class FindRecipeCommand(sublime_plugin.TextCommand):
	_cookbooks_path="/Users/juliabiro/.prezi/prezi-chef/cookbooks/"
	_roles_path="/Users/juliabiro/.prezi/prezi-chef/roles/"

	def run(self, edit):
		def done(filename):
			self.view.window().open_file(filename, sublime.ENCODED_POSITION)

		sels=self.view.sel()
		for s in sels:
			if self._is_recipe(s):
				if self._is_included_recipe(s):
					filename = self._find_recipe_path(self._get_full_recipe_name2(s)) 
				else:
					filename = self._find_recipe_path(self._get_full_recipe_name(s))
			elif self._is_role(s):
				filename = self._find_role_path(self._get_full_recipe_name(s))
		
		self.view.window().show_input_panel("file to open: ", filename, done, None, None)

	def _get_full_recipe_name(self, selection):
		line = self.view.line(selection)
		open = self.view.find('\[', line.begin())
		close = self.view.find('\]', line.begin())
		return self.view.substr(sublime.Region(open.begin()+1,close.end()-1))

	def _get_full_recipe_name2(self, selection):
		line = self.view.line(selection)
		open = self.view.find('\"', line.begin())
		close = self.view.find('\"', open.begin()+1)
		return self.view.substr(sublime.Region(open.begin()+1,close.end()-1))

	def _is_recipe(self, selection):
		line = self.view.line(selection)
		return line.contains(self.view.find("recipe", line.begin()))

	def _is_included_recipe(self, selection):
		line = self.view.line(selection)
		return self.view.find("include_recipe", line.begin()) and line.contains(self.view.find("include_recipe", line.begin()))
		
	def _is_role(self, selection):
		line = self.view.line(selection)
		return line.contains(self.view.find("role", line.begin()))
		
	def _find_recipe_path(self, recipe_name):
		# case 2: recipe name only
		# case 1: cookbook name:: recipe name
		delim = recipe_name.find("::")
		if  delim == -1:
			return self._cookbooks_path+recipe_name+"/recipes/default.rb"
		else:
			return self._cookbooks_path+recipe_name[:delim]+"/recipes/"+recipe_name[delim+2:]+".rb"

	def _find_role_path(self,role_name):
		return self._roles_path+role_name+".json"

"""
recipe "[users]"
"""
