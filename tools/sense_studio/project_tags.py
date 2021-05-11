import urllib

from flask import Blueprint
from flask import redirect
from flask import request
from flask import url_for

from tools.sense_studio import project_utils

tags_bp = Blueprint('tags_bp', __name__)


@tags_bp.route('/create-project-tag/<string:project>', methods=['POST'])
def create_tag(project):
    data = request.form
    project = urllib.parse.unquote(project)
    path = project_utils.lookup_project_path(project)
    config = project_utils.load_project_config(path)
    tag_name = data['newTagName']

    project_tags = config['project_tags']
    new_tag_index = config['max_tag_index'] + 1
    project_tags[new_tag_index] = tag_name
    config['max_tag_index'] = new_tag_index

    project_utils.write_project_config(path, config)
    return redirect(url_for('project_details', project=project))


@tags_bp.route('/remove-project-tag/<string:project>/<int:tag_idx>')
def remove_tag(project, tag_idx):
    project = urllib.parse.unquote(project)
    path = project_utils.lookup_project_path(project)
    config = project_utils.load_project_config(path)
    project_tags = config['project_tags']

    # Remove tag from the project tags list
    del project_tags[tag_idx]

    # Remove tag from the classes
    for class_label, tags in config['classes'].items():
        if tag_idx in tags:
            tags.remove(tag_idx)

    project_utils.write_project_config(path, config)
    return redirect(url_for('project_details', project=project))


@tags_bp.route('/edit-project-tag/<string:project>/<int:tag_idx>', methods=['POST'])
def edit_tag(project, tag_idx):
    data = request.form
    project = urllib.parse.unquote(project)
    path = project_utils.lookup_project_path(project)
    config = project_utils.load_project_config(path)
    project_tags = config['project_tags']
    new_tag_name = data['newTagName']

    # Update tag name
    project_tags[tag_idx] = new_tag_name

    project_utils.write_project_config(path, config)
    return redirect(url_for('project_details', project=project))
