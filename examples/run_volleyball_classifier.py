#!/usr/bin/env python
"""
Run a custom classifier that was obtained via the train_classifier script.

Usage:
  run_custom_classifier.py --custom_classifier=PATH
                           [--camera_id=CAMERA_ID]
                           [--path_in=FILENAME]
                           [--path_out=FILENAME]
                           [--title=TITLE]
                           [--use_gpu]
  run_custom_classifier.py (-h | --help)

Options:
  --custom_classifier=PATH   Path to the custom classifier to use
  --path_in=FILENAME         Video file to stream from
  --path_out=FILENAME        Video file to stream to
  --title=TITLE              This adds a title to the window display
"""
import os
import json
from docopt import docopt

import sense.display
from sense import engine
from sense.backbone_networks.efficientnet import StridedInflatedEfficientNet
from sense.controller import Controller
from sense.downstream_tasks.nn_utils import Pipe, LogisticRegression
from sense.downstream_tasks.postprocess import PostprocessClassificationOutput, OnePositionRepCounter
from sense.downstream_tasks.postprocess import TwoPositionsRepCounter


if __name__ == "__main__":
    # Parse arguments
    args = docopt(__doc__)
    camera_id = args['--camera_id'] or 0
    path_in = args['--path_in'] or None
    path_out = args['--path_out'] or None
    custom_classifier = args['--custom_classifier'] or None
    title = args['--title'] or None
    use_gpu = args['--use_gpu']

    # Load original feature extractor
    feature_extractor = StridedInflatedEfficientNet()
    checkpoint = engine.load_weights('resources/backbone/strided_inflated_efficientnet.ckpt')

    # Load custom classifier
    checkpoint_classifier = engine.load_weights(os.path.join(custom_classifier, 'classifier.checkpoint'))
    # Update original weights in case some intermediate layers have been finetuned
    name_finetuned_layers = set(checkpoint.keys()).intersection(checkpoint_classifier.keys())
    for key in name_finetuned_layers:
        checkpoint[key] = checkpoint_classifier.pop(key)
    feature_extractor.load_state_dict(checkpoint)
    feature_extractor.eval()

    with open(os.path.join(custom_classifier, 'label2int.json')) as file:
        class2int = json.load(file)
    INT2LAB = {value: key for key, value in class2int.items()}

    gesture_classifier = LogisticRegression(num_in=feature_extractor.feature_dim,
                                            num_out=len(INT2LAB))
    gesture_classifier.load_state_dict(checkpoint_classifier)
    gesture_classifier.eval()

    # Concatenate feature extractor and met converter
    net = Pipe(feature_extractor, gesture_classifier)

    postprocessor = [
        PostprocessClassificationOutput(INT2LAB, smoothing=4),
        # v1: 0.1
        # OnePositionRepCounter(mapping=class2int,
        #                       position='forearm_passing_position_1',
        #                       threshold=0.05,
        #                       out_key='forearm passes'),
        # OnePositionRepCounter(mapping=class2int,
        #                       position='overhead_passing_position_1',
        #                       threshold=0.1,
        #                       out_key='overhead passes'),
        # OnePositionRepCounter(mapping=class2int,
        #                       position='pokey_position_1',
        #                       threshold=0.2,
        #                       out_key='pokeys'),
        # OnePositionRepCounter(mapping=class2int,
        #                       position='one_arm_passing_position_1',
        #                       threshold=0.1,
        #                       out_key='one arm passes'),
        # OnePositionRepCounter(mapping=class2int,
        #                       position='bouncing_ball_position_1',
        #                       threshold=0.2,
        #                       out_key='bounces'),
        # OnePositionRepCounter(mapping=class2int,
        #                       position='dropping_ball_position_1',
        #                       threshold=0.1,
        #                       out_key='dropped'),
        # v1: 0.2
        TwoPositionsRepCounter(mapping=class2int,
                               position0='forearm_passing_position_1',
                               position1='forearm_passing_position_2',
                               threshold0=0.1,
                               threshold1=0.05,
                               out_key='forearm passes'),
        TwoPositionsRepCounter(mapping=class2int,
                               position0='overhead_passing_position_1',
                               position1='overhead_passing_position_2',
                               threshold0=0.18,  # v2: 0.2 v3: 0.15
                               threshold1=0.18,  # v2: 0.2 v3: 0.15
                               out_key='overhead passes'),
        TwoPositionsRepCounter(mapping=class2int,
                               position0='pokey_position_1',
                               position1='pokey_position_2',
                               threshold0=0.1,
                               threshold1=0.1,
                               out_key='pokeys'),
        TwoPositionsRepCounter(mapping=class2int,
                               position0='one_arm_passing_position_1',
                               position1='one_arm_passing_position_2',
                               threshold0=0.2,  # v2: 0.1
                               threshold1=0.2,  # v2: 0.1
                               out_key='one arm passes'),
        TwoPositionsRepCounter(mapping=class2int,
                               position0='bouncing_ball_position_1',
                               position1='bouncing_ball_position_2',
                               threshold0=0.1,
                               threshold1=0.1,
                               out_key='bounces'),
    ]

    display_ops = [
        # realtimenet.display.DisplayTopKClassificationOutputs(top_k=1, threshold=0),
        sense.display.DisplayTopKClassificationOutputs(top_k=3, threshold=0),
        sense.display.DisplayRepCounts2(keys=[
            'forearm passes',
            'overhead passes',
            'pokeys',
            'one arm passes',
            'bounces',
            # 'dropped',
        ], y_offset=120)
    ]
    display_results = sense.display.DisplayResults(title=title, display_ops=display_ops, border_size=100)
    # display_results = realtimenet.display.DisplayResults(title=title, display_ops=display_ops)

    # Run live inference
    controller = Controller(
        neural_network=net,
        post_processors=postprocessor,
        results_display=display_results,
        callbacks=[],
        camera_id=camera_id,
        path_in=path_in,
        path_out=path_out,
        use_gpu=use_gpu
    )
    controller.run_inference()
