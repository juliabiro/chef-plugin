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
				self._roles_path=os.path.realpath(os.path.join(self._cookbooks_path, "../roles/"))

			return (self._cookbooks_path and self._roles_path)

		return (self._cookbooks_path and self._roles_path) or update_chef_root()


	def _get_recipe_name(view, line, delim1='\[', delim2='\]'):
			open = view.find(delim1, line.begin())
			close = view.find(delim2, open.begin()+1)
			return view.substr(sublime.Region(open.begin()+1,close.end()-1))


class BuildRecipeTree(FindRecipeCommand):
	# TODO: first I need a full recipe tree. No way around that
	# 1. find run_list dict, create start set from it
	# 2. create emty recipe tree
	# 3. copy all recipes from start list to recipe tree
	# 4. make a list just from the roles
	# 5. expand roles runlists into a new start list
	# repeat 3-5 until start list is empty

	_recipes_tree={}
	
	

	def run(self, edit):
		if not self._validate_chef_root():
			return

		def _get_name(name):
			s=name.find('[')
			e=name.find(']', s+1)
			return name[s+1:e]

		import json
		selection = sublime.Region(0, self.view.size())
		all_json=None
		try:
			all_json=json.loads(self.view.substr(selection))
		except Exception as e:
			print(e, "not a json file")
		
		runlist=all_json["run_list"]
		while runlist!=[]:
			print("recipes_tree: ", self._recipes_tree)
			roles_list=[x for x in runlist if x and x.startswith("role")]
			recipes_list=[x for x in runlist if x and x.startswith("recipe")]
			
			for recipe in recipes_list:
				self._copy_recipe_to_tree(_get_name(recipe))

			runlist=[]
			for role in roles_list:
				runlist.extend(self._get_role_runlist(_get_name(role)))

		
	def _copy_recipe_to_tree(self, recipe_name):
		if recipe_name.find("::")!=-1:
			delim=recipe_name.find('::')
			if self._recipes_tree.has_key(recipe_name[:delim]):
				self._recipes_tree[recipe_name[:delim]].append(recipe_name[delim+2:])
			else:
				self._recipes_tree[recipe_name[:delim]]=[recipe_name[delim+2:]]
		else:
			self._recipes_tree[recipe_name]=['default']
	
	def _get_role_runlist(self, role_name):
		import os
		import json
		role_file=os.path.join(self._roles_path, role_name+".json")

		#read role file
		# find runlist
		try:
			rolefile=open(role_file, "r")
			rl=json.loads(rolefile.read())
			return rl["run_list"]
		except Exception as e:
			print(e)


# TODO: parse json for default attributes, override_attribtes, and for normal tag in nodes