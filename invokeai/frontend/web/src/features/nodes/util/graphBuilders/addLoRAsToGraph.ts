import { RootState } from 'app/store/store';
import { NonNullableGraph } from 'features/nodes/types/types';
import { forEach, size } from 'lodash-es';
import { LoraLoaderInvocation } from 'services/api/types';
import { modelIdToLoRAModelField } from '../modelIdToLoRAName';
import {
  LORA_LOADER,
  MAIN_MODEL_LOADER,
  NEGATIVE_CONDITIONING,
  POSITIVE_CONDITIONING,
} from './constants';

export const addLoRAsToGraph = (
  graph: NonNullableGraph,
  state: RootState,
  baseNodeId: string
): void => {
  /**
   * LoRA nodes get the UNet and CLIP models from the main model loader and apply the LoRA to them.
   * They then output the UNet and CLIP models references on to either the next LoRA in the chain,
   * or to the inference/conditioning nodes.
   *
   * So we need to inject a LoRA chain into the graph.
   */

  const { loras } = state.lora;
  const loraCount = size(loras);

  if (loraCount > 0) {
    // remove any existing connections from main model loader, we need to insert the lora nodes
    graph.edges = graph.edges.filter(
      (e) =>
        !(
          e.source.node_id === MAIN_MODEL_LOADER &&
          ['unet', 'clip'].includes(e.source.field)
        )
    );
  }

  // we need to remember the last lora so we can chain from it
  let lastLoraNodeId = '';
  let currentLoraIndex = 0;

  forEach(loras, (lora) => {
    const { id, name, weight } = lora;
    const loraField = modelIdToLoRAModelField(id);
    const currentLoraNodeId = `${LORA_LOADER}_${loraField.model_name.replace(
      '.',
      '_'
    )}`;

    const loraLoaderNode: LoraLoaderInvocation = {
      type: 'lora_loader',
      id: currentLoraNodeId,
      lora: loraField,
      weight,
    };

    graph.nodes[currentLoraNodeId] = loraLoaderNode;

    if (currentLoraIndex === 0) {
      // first lora = start the lora chain, attach directly to model loader
      graph.edges.push({
        source: {
          node_id: MAIN_MODEL_LOADER,
          field: 'unet',
        },
        destination: {
          node_id: currentLoraNodeId,
          field: 'unet',
        },
      });

      graph.edges.push({
        source: {
          node_id: MAIN_MODEL_LOADER,
          field: 'clip',
        },
        destination: {
          node_id: currentLoraNodeId,
          field: 'clip',
        },
      });
    } else {
      // we are in the middle of the lora chain, instead connect to the previous lora
      graph.edges.push({
        source: {
          node_id: lastLoraNodeId,
          field: 'unet',
        },
        destination: {
          node_id: currentLoraNodeId,
          field: 'unet',
        },
      });
      graph.edges.push({
        source: {
          node_id: lastLoraNodeId,
          field: 'clip',
        },
        destination: {
          node_id: currentLoraNodeId,
          field: 'clip',
        },
      });
    }

    if (currentLoraIndex === loraCount - 1) {
      // final lora, end the lora chain - we need to connect up to inference and conditioning nodes
      graph.edges.push({
        source: {
          node_id: currentLoraNodeId,
          field: 'unet',
        },
        destination: {
          node_id: baseNodeId,
          field: 'unet',
        },
      });

      graph.edges.push({
        source: {
          node_id: currentLoraNodeId,
          field: 'clip',
        },
        destination: {
          node_id: POSITIVE_CONDITIONING,
          field: 'clip',
        },
      });

      graph.edges.push({
        source: {
          node_id: currentLoraNodeId,
          field: 'clip',
        },
        destination: {
          node_id: NEGATIVE_CONDITIONING,
          field: 'clip',
        },
      });
    }

    // increment the lora for the next one in the chain
    lastLoraNodeId = currentLoraNodeId;
    currentLoraIndex += 1;
  });
};
