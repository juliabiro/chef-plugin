import sublime, sublime_plugin

class FindRecipeCommand(sublime_plugin.TextCommand):
	_cookbooks_path="/Users/juliabiro/.prezi/prezi-chef/cookbooks/"
	
	def run(self, edit):
		print(self._get_selected_text())
		#self.view.insert(edit, 0, self._find_recipe_path())


	def _get_selected_text(self):
		sels=self.view.sel()
		for s in sels:
			return(self.view.substr(s))

	def _find_recipe_path(self):

		return str(self._get_selected_text())