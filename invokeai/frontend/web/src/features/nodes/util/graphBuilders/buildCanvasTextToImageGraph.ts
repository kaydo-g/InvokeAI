import { RootState } from 'app/store/store';
import { NonNullableGraph } from 'features/nodes/types/types';
import { addControlNetToLinearGraph } from '../addControlNetToLinearGraph';
import { modelIdToMainModelField } from '../modelIdToMainModelField';
import { addDynamicPromptsToGraph } from './addDynamicPromptsToGraph';
import { addLoRAsToGraph } from './addLoRAsToGraph';
import { addVAEToGraph } from './addVAEToGraph';
import {
  LATENTS_TO_IMAGE,
  MAIN_MODEL_LOADER,
  NEGATIVE_CONDITIONING,
  NOISE,
  POSITIVE_CONDITIONING,
  TEXT_TO_IMAGE_GRAPH,
  TEXT_TO_LATENTS,
} from './constants';

/**
 * Builds the Canvas tab's Text to Image graph.
 */
export const buildCanvasTextToImageGraph = (
  state: RootState
): NonNullableGraph => {
  const {
    positivePrompt,
    negativePrompt,
    model: modelId,
    cfgScale: cfg_scale,
    scheduler,
    steps,
    iterations,
    seed,
    shouldRandomizeSeed,
  } = state.generation;

  // The bounding box determines width and height, not the width and height params
  const { width, height } = state.canvas.boundingBoxDimensions;

  const model = modelIdToMainModelField(modelId);

  /**
   * The easiest way to build linear graphs is to do it in the node editor, then copy and paste the
   * full graph here as a template. Then use the parameters from app state and set friendlier node
   * ids.
   *
   * The only thing we need extra logic for is handling randomized seed, control net, and for img2img,
   * the `fit` param. These are added to the graph at the end.
   */

  // copy-pasted graph from node editor, filled in with state values & friendly node ids
  const graph: NonNullableGraph = {
    id: TEXT_TO_IMAGE_GRAPH,
    nodes: {
      [POSITIVE_CONDITIONING]: {
        type: 'compel',
        id: POSITIVE_CONDITIONING,
        prompt: positivePrompt,
      },
      [NEGATIVE_CONDITIONING]: {
        type: 'compel',
        id: NEGATIVE_CONDITIONING,
        prompt: negativePrompt,
      },
      [NOISE]: {
        type: 'noise',
        id: NOISE,
        width,
        height,
      },
      [TEXT_TO_LATENTS]: {
        type: 't2l',
        id: TEXT_TO_LATENTS,
        cfg_scale,
        scheduler,
        steps,
      },
      [MAIN_MODEL_LOADER]: {
        type: 'main_model_loader',
        id: MAIN_MODEL_LOADER,
        model,
      },
      [LATENTS_TO_IMAGE]: {
        type: 'l2i',
        id: LATENTS_TO_IMAGE,
      },
    },
    edges: [
      {
        source: {
          node_id: NEGATIVE_CONDITIONING,
          field: 'conditioning',
        },
        destination: {
          node_id: TEXT_TO_LATENTS,
          field: 'negative_conditioning',
        },
      },
      {
        source: {
          node_id: POSITIVE_CONDITIONING,
          field: 'conditioning',
        },
        destination: {
          node_id: TEXT_TO_LATENTS,
          field: 'positive_conditioning',
        },
      },
      {
        source: {
          node_id: MAIN_MODEL_LOADER,
          field: 'clip',
        },
        destination: {
          node_id: POSITIVE_CONDITIONING,
          field: 'clip',
        },
      },
      {
        source: {
          node_id: MAIN_MODEL_LOADER,
          field: 'clip',
        },
        destination: {
          node_id: NEGATIVE_CONDITIONING,
          field: 'clip',
        },
      },
      {
        source: {
          node_id: MAIN_MODEL_LOADER,
          field: 'unet',
        },
        destination: {
          node_id: TEXT_TO_LATENTS,
          field: 'unet',
        },
      },
      {
        source: {
          node_id: TEXT_TO_LATENTS,
          field: 'latents',
        },
        destination: {
          node_id: LATENTS_TO_IMAGE,
          field: 'latents',
        },
      },
      {
        source: {
          node_id: NOISE,
          field: 'noise',
        },
        destination: {
          node_id: TEXT_TO_LATENTS,
          field: 'noise',
        },
      },
    ],
  };

  addLoRAsToGraph(graph, state, TEXT_TO_LATENTS);

  // Add VAE
  addVAEToGraph(graph, state);

  // add dynamic prompts, mutating `graph`
  addDynamicPromptsToGraph(graph, state);

  // add controlnet, mutating `graph`
  addControlNetToLinearGraph(graph, TEXT_TO_LATENTS, state);

  return graph;
};
