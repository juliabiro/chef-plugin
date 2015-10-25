import sublime, sublime_plugin

class FindRecipeCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.insert(edit, 0, self._find_recipe_path())


	def _find_recipe_path(self):
		return "Hello World!"