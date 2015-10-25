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
			line = self.view.line(s)
			filename= self.get_recipe_path_from_line(line)
			if filename:
				self.view.window().open_file(filename, sublime.ENCODED_POSITION)

			
	
	def get_recipe_path_from_line(self, line):
		filename=None

		def _get_recipe_name(view, line, delim1='\[', delim2='\]'):
			open = view.find(delim1, line.begin())
			close = view.find(delim2, open.begin()+1)
			return view.substr(sublime.Region(open.begin()+1,close.end()-1))

		def _does_contain_keyword(view, line, keyword):
			return view.find(keyword, line.begin()) and line.contains(view.find(keyword, line.begin()))
	
		def _make_recipe_path(cookbooks_path, recipe_name):
			# case 2: recipe name only
			# case 1: cookbook name:: recipe name
			delim = recipe_name.find("::")
			if  delim == -1:
				return cookbooks_path+recipe_name+"/recipes/default.rb"
			else:
				return cookbooks_path+recipe_name[:delim]+"/recipes/"+recipe_name[delim+2:]+".rb"

		def _make_role_path(roles_path,role_name):
			return roles_path+role_name+".json"


		if _does_contain_keyword(self.view, line, "recipe"):
				if _does_contain_keyword(self.view, line, "include_recipe"):
					filename = _make_recipe_path(self._cookbooks_path, _get_recipe_name(self.view, line, delim1='\"', delim2='\"')) 
				else:
					filename = _make_recipe_path(self._cookbooks_path, _get_recipe_name(self.view, line))

		elif _does_contain_keyword(self.view,line, "role"):
				filename = _make_role_path(self._roles_path, _get_recipe_name(self.view, line))
		
		return filename



#########################################################
# validate cookbook path and role path
# return false if none can be found
#########################################################
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

