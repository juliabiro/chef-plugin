# Chef plugin

Plugin for navigating big chef repos.
This project is a beta version, please test and give feedback.

## Features
* Open the recipe or role mentioned in the current line (default: Cmd + Alt + j)
* Expand runlist of currently opened role or node file (default: Cmd + Alt + k)
* Find usages of an attribute defined in the current line by expanding the runlist of the currently opened role or node file and searching through occurrences (default: Cmd + Alt + l)

You can modify the key bindings by editing the appropriate .sublime-keymap file in the repo.

## Installation
`cd ~/Library/Application\ Support/Sublime\ Text\ 2/Packages` (assuming that is where your Sublime installation is)
`git clone git@github.com:juliabiro/chef-plugin`
`git checkout cleanup`

You might have to restart Sublime.