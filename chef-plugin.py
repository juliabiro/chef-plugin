import sublime, sublime_plugin

class FindRecipeCommand(sublime_plugin.TextCommand):
	_cookbooks_path=None
	_roles_path=None

	def run(self, edit):
		if not self._validate_chef_root():
			return

		sels=self.view.sel()
		for s in sels:
			filename=None
			if self._is_recipe(s):
				if self._is_included_recipe(s):
					filename = self._find_recipe_path(self._get_recipe_name(s, delim1='\"', delim2='\"')) 
					print (filename)
				else:
					filename = self._find_recipe_path(self._get_recipe_name(s))
			elif self._is_role(s):
				filename = self._find_role_path(self._get_recipe_name(s))
		
			if filename:
				self.view.window().open_file(filename, sublime.ENCODED_POSITION)
		
	def _get_recipe_name(self, selection, delim1='\[', delim2='\]'):
		line = self.view.line(selection)
		open = self.view.find(delim1, line.begin())
		close = self.view.find(delim2, open.begin()+1)
		return self.view.substr(sublime.Region(open.begin()+1,close.end()-1))

	def _is_recipe(self, selection):
		line = self.view.line(selection)
		return self.view.find("recipe", line.begin()) and line.contains(self.view.find("recipe", line.begin()))

	def _is_included_recipe(self, selection):
		line = self.view.line(selection)
		return self.view.find("include_recipe", line.begin()) and line.contains(self.view.find("include_recipe", line.begin()))
		
	def _is_role(self, selection):
		line = self.view.line(selection)
		return self.view.find("role", line.begin()) and line.contains(self.view.find("role", line.begin()))
		
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

	# make sure that we have a chef root somewhere. 
	# if already set, check if we are on thhe path
	# if not, make sure to find one 
	def _validate_chef_root(self):
		import os
		def update_chef_root():

			def find_cookbook_dir():
				
				cbp = None
				current_dir=os.path.dirname(os.path.realpath(self.view.file_name()))
				
				i=100
				while i>0 and not cbp and os.path.dirname(current_dir) != current_dir:
					for dirs in os.listdir(current_dir):
						if dirs.endswith("cookbooks"):
							cbp= os.path.join(current_dir, dirs+"/")
							break
					current_dir=os.path.realpath(os.path.join(current_dir, os.pardir))
					i=i-1
				return cbp
					
			self._cookbooks_path=find_cookbook_dir()
			
			if self._cookbooks_path!=None:
				self._roles_path=os.path.join(self._cookbooks_path, "../roles/")

			return (self._cookbooks_path and self._roles_path)

		return (self._cookbooks_path and self._roles_path) or update_chef_root()


"""
recipe "[users]"
"""
