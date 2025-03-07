"""This module manages the InvokeAI `models.yaml` file, mapping
symbolic diffusers model names to the paths and repo_ids used by the
underlying `from_pretrained()` call.

SYNOPSIS:

 mgr = ModelManager('/home/phi/invokeai/configs/models.yaml')
 sd1_5 = mgr.get_model('stable-diffusion-v1-5',
                       model_type=ModelType.Main,
                       base_model=BaseModelType.StableDiffusion1,
                       submodel_type=SubModelType.Unet)
 with sd1_5 as unet:
    run_some_inference(unet)

FETCHING MODELS:

Models are described using four attributes:

  1) model_name -- the symbolic name for the model

  2) ModelType  -- an enum describing the type of the model. Currently
                  defined types are:
         ModelType.Main -- a full model capable of generating images
         ModelType.Vae  -- a VAE model
         ModelType.Lora -- a LoRA or LyCORIS fine-tune
         ModelType.TextualInversion -- a textual inversion embedding
         ModelType.ControlNet -- a ControlNet model

  3) BaseModelType -- an enum indicating the stable diffusion base model, one of:
         BaseModelType.StableDiffusion1
         BaseModelType.StableDiffusion2

  4) SubModelType (optional) -- an enum that refers to one of the submodels contained
                                within the main model. Values are:

         SubModelType.UNet
         SubModelType.TextEncoder
         SubModelType.Tokenizer
         SubModelType.Scheduler
         SubModelType.SafetyChecker

To fetch a model, use `manager.get_model()`. This takes the symbolic
name of the model, the ModelType, the BaseModelType and the
SubModelType. The latter is required for ModelType.Main.

get_model() will return a ModelInfo object that can then be used in
context to retrieve the model and move it into GPU VRAM (on GPU
systems).

A typical example is:

 sd1_5 = mgr.get_model('stable-diffusion-v1-5',
                       model_type=ModelType.Main,
                       base_model=BaseModelType.StableDiffusion1,
                       submodel_type=SubModelType.Unet)
 with sd1_5 as unet:
    run_some_inference(unet)

The ModelInfo object provides a number of useful fields describing the
model, including:

   name  -- symbolic name of the model
   base_model -- base model (BaseModelType)
   type -- model type (ModelType)
   location -- path to the model file
   precision -- torch precision of the model
   hash -- unique sha256 checksum for this model

SUBMODELS:

When fetching a main model, you must specify the submodel. Retrieval
of full pipelines is not supported.

 vae_info = mgr.get_model('stable-diffusion-1.5',
                          model_type = ModelType.Main,
                          base_model = BaseModelType.StableDiffusion1,
                          submodel_type = SubModelType.Vae
                          )
 with vae_info as vae:
    do_something(vae)

This rule does not apply to controlnets, embeddings, loras and standalone
VAEs, which do not have submodels.

LISTING MODELS

The model_names() method will return a list of Tuples describing each
model it knows about:

  >> mgr.model_names()
  [
    ('stable-diffusion-1.5', <BaseModelType.StableDiffusion1: 'sd-1'>, <ModelType.Main: 'main'>),
    ('stable-diffusion-2.1', <BaseModelType.StableDiffusion2: 'sd-2'>, <ModelType.Main: 'main'>),
    ('inpaint', <BaseModelType.StableDiffusion1: 'sd-1'>, <ModelType.ControlNet: 'controlnet'>)
    ('Ink scenery', <BaseModelType.StableDiffusion1: 'sd-1'>, <ModelType.Lora: 'lora'>)
    ...
  ]

The tuple is in the correct order to pass to get_model():

   for m in mgr.model_names():
       info = get_model(*m)

In contrast, the list_models() method returns a list of dicts, each
providing information about a model defined in models.yaml. For example:

   >>> models = mgr.list_models()
   >>> json.dumps(models[0])
  {"path": "/home/lstein/invokeai-main/models/sd-1/controlnet/canny", 
    "model_format": "diffusers", 
    "name": "canny", 
    "base_model": "sd-1", 
    "type": "controlnet"
   }

You can filter by model type and base model as shown here:

  
  controlnets = mgr.list_models(model_type=ModelType.ControlNet,
                                base_model=BaseModelType.StableDiffusion1)
  for c in controlnets:
     name = c['name']
     format = c['model_format']
     path = c['path']
     type = c['type']
     # etc

ADDING AND REMOVING MODELS

At startup time, the `models` directory will be scanned for
checkpoints, diffusers pipelines, controlnets, LoRAs and TI
embeddings. New entries will be added to the model manager and defunct
ones removed. Anything that is a main model (ModelType.Main) will be
added to models.yaml. For scanning to succeed, files need to be in
their proper places. For example, a controlnet folder built on the
stable diffusion 2 base, will need to be placed in
`models/sd-2/controlnet`.

Layout of the `models` directory:

 models
 ├── sd-1
 │   ├── controlnet
 │   ├── lora
 │   ├── main
 │   └── embedding
 ├── sd-2
 │   ├── controlnet
 │   ├── lora
 │   ├── main
 │   └── embedding
 └── core
     ├── face_reconstruction
     │   ├── codeformer
     │   └── gfpgan
     ├── sd-conversion
     │   ├── clip-vit-large-patch14 - tokenizer, text_encoder subdirs
     │   ├── stable-diffusion-2 - tokenizer, text_encoder subdirs
     │   └── stable-diffusion-safety-checker
     └── upscaling
         └─── esrgan



class ConfigMeta(BaseModel):Loras, textual_inversion and controlnet models are not listed
explicitly in models.yaml, but are added to the in-memory data
structure at initialization time by scanning the models directory. The
in-memory data structure can be resynchronized by calling
`manager.scan_models_directory()`.

Files and folders placed inside the `autoimport` paths (paths
defined in `invokeai.yaml`) will also be scanned for new models at
initialization time and added to `models.yaml`. Files will not be
moved from this location but preserved in-place. These directories
are:

  configuration    default              description
  -------------    -------              -----------
  autoimport_dir  autoimport/main       main models
  lora_dir        autoimport/lora       LoRA/LyCORIS models
  embedding_dir   autoimport/embedding  TI embeddings
  controlnet_dir  autoimport/controlnet ControlNet models

In actuality, models located in any of these directories are scanned
to determine their type, so it isn't strictly necessary to organize
the different types in this way. This entry in `invokeai.yaml` will
recursively scan all subdirectories within `autoimport`, scan models
files it finds, and import them if recognized.

  Paths:
     autoimport_dir: autoimport

A model can be manually added using `add_model()` using the model's
name, base model, type and a dict of model attributes. See
`invokeai/backend/model_management/models` for the attributes required
by each model type.

A model can be deleted using `del_model()`, providing the same 
identifying information as `get_model()`

The `heuristic_import()` method will take a set of strings
corresponding to local paths, remote URLs, and repo_ids, probe the
object to determine what type of model it is (if any), and import new
models into the manager. If passed a directory, it will recursively
scan it for models to import. The return value is a set of the models
successfully added.

MODELS.YAML

The general format of a models.yaml section is:

 type-of-model/name-of-model:
     path: /path/to/local/file/or/directory
     description: a description
     format: diffusers|checkpoint
     variant: normal|inpaint|depth

The type of model is given in the stanza key, and is one of
{main, vae, lora, controlnet, textual}

The format indicates whether the model is organized as a diffusers
folder with model subdirectories, or is contained in a single
checkpoint or safetensors file.

The path points to a file or directory on disk. If a relative path,
the root is the InvokeAI ROOTDIR.

"""
from __future__ import annotations

import os
import hashlib
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple, Union, Dict, Set, Callable, types
from shutil import rmtree, move

import torch
from omegaconf import OmegaConf
from omegaconf.dictconfig import DictConfig

from pydantic import BaseModel, Field

import invokeai.backend.util.logging as logger
from invokeai.app.services.config import InvokeAIAppConfig
from invokeai.backend.util import CUDA_DEVICE, Chdir
from .model_cache import ModelCache, ModelLocker
from .models import (
    BaseModelType, ModelType, SubModelType,
    ModelError, SchedulerPredictionType, MODEL_CLASSES,
    ModelConfigBase, ModelNotFoundException,
    )

# We are only starting to number the config file with release 3.
# The config file version doesn't have to start at release version, but it will help
# reduce confusion.
CONFIG_FILE_VERSION='3.0.0'

@dataclass
class ModelInfo():
    context: ModelLocker
    name: str
    base_model: BaseModelType
    type: ModelType
    hash: str
    location: Union[Path, str]
    precision: torch.dtype
    _cache: ModelCache = None

    def __enter__(self):
        return self.context.__enter__()

    def __exit__(self,*args, **kwargs):
        self.context.__exit__(*args, **kwargs)

class InvalidModelError(Exception):
    "Raised when an invalid model is requested"
    pass

class AddModelResult(BaseModel):
    name: str = Field(description="The name of the model after installation")
    model_type: ModelType = Field(description="The type of model")
    base_model: BaseModelType = Field(description="The base model")
    config: ModelConfigBase = Field(description="The configuration of the model")

MAX_CACHE_SIZE = 6.0  # GB

class ConfigMeta(BaseModel):
    version: str

class ModelManager(object):
    """
    High-level interface to model management.
    """

    logger: types.ModuleType = logger

    def __init__(
        self,
        config: Union[Path, DictConfig, str],
        device_type: torch.device = CUDA_DEVICE,
        precision: torch.dtype = torch.float16,
        max_cache_size=MAX_CACHE_SIZE,
        sequential_offload=False,
        logger: types.ModuleType = logger,
    ):
        """
        Initialize with the path to the models.yaml config file. 
        Optional parameters are the torch device type, precision, max_models,
        and sequential_offload boolean. Note that the default device
        type and precision are set up for a CUDA system running at half precision.
        """

        self.config_path = None
        if isinstance(config, (str, Path)):
            self.config_path = Path(config)
            config = OmegaConf.load(self.config_path)

        elif not isinstance(config, DictConfig):
            raise ValueError('config argument must be an OmegaConf object, a Path or a string')

        self.config_meta = ConfigMeta(**config.pop("__metadata__"))
        # TODO: metadata not found
        # TODO: version check

        self.models = dict()
        for model_key, model_config in config.items():
            model_name, base_model, model_type = self.parse_key(model_key)
            model_class = MODEL_CLASSES[base_model][model_type]
            # alias for config file
            model_config["model_format"] = model_config.pop("format")
            self.models[model_key] = model_class.create_config(**model_config)

        # check config version number and update on disk/RAM if necessary
        self.app_config = InvokeAIAppConfig.get_config()
        self.logger = logger
        self.cache = ModelCache(
            max_cache_size=max_cache_size,
            execution_device = device_type,
            precision = precision,
            sequential_offload = sequential_offload,
            logger = logger,
        )
        self.cache_keys = dict()

        # add controlnet, lora and textual_inversion models from disk
        self.scan_models_directory()

    def model_exists(
        self,
        model_name: str,
        base_model: BaseModelType,
        model_type: ModelType,
    ) -> bool:
        """
        Given a model name, returns True if it is a valid
        identifier.
        """
        model_key = self.create_key(model_name, base_model, model_type)
        return model_key in self.models

    @classmethod
    def create_key(
        cls,
        model_name: str,
        base_model: BaseModelType,
        model_type: ModelType,
    ) -> str:
        return f"{base_model}/{model_type}/{model_name}"

    @classmethod
    def parse_key(cls, model_key: str) -> Tuple[str, BaseModelType, ModelType]:
        base_model_str, model_type_str, model_name = model_key.split('/', 2)
        try:
            model_type = ModelType(model_type_str)
        except:
            raise Exception(f"Unknown model type: {model_type_str}")

        try:
            base_model = BaseModelType(base_model_str)
        except:
            raise Exception(f"Unknown base model: {base_model_str}")

        return (model_name, base_model, model_type)

    def _get_model_cache_path(self, model_path):
        return self.app_config.models_path / ".cache" / hashlib.md5(str(model_path).encode()).hexdigest()

    def get_model(
        self,
        model_name: str,
        base_model: BaseModelType,
        model_type: ModelType,
        submodel_type: Optional[SubModelType] = None
    )->ModelInfo:
        """Given a model named identified in models.yaml, return
        an ModelInfo object describing it.
        :param model_name: symbolic name of the model in models.yaml
        :param model_type: ModelType enum indicating the type of model to return
        :param base_model: BaseModelType enum indicating the base model used by this model
        :param submode_typel: an ModelType enum indicating the portion of 
               the model to retrieve (e.g. ModelType.Vae)
        """
        model_class = MODEL_CLASSES[base_model][model_type]
        model_key = self.create_key(model_name, base_model, model_type)

        # if model not found try to find it (maybe file just pasted)
        if model_key not in self.models:
            self.scan_models_directory(base_model=base_model, model_type=model_type)
            if model_key not in self.models:
                raise ModelNotFoundException(f"Model not found - {model_key}")

        model_config = self.models[model_key]
        model_path = self.app_config.root_path / model_config.path

        if not model_path.exists():
            if model_class.save_to_config:
                self.models[model_key].error = ModelError.NotFound
                raise Exception(f"Files for model \"{model_key}\" not found")

            else:
                self.models.pop(model_key, None)
                raise ModelNotFoundException(f"Model not found - {model_key}")

        # vae/movq override
        # TODO: 
        if submodel_type is not None and hasattr(model_config, submodel_type):
            override_path = getattr(model_config, submodel_type)
            if override_path:
                model_path = self.app_config.root_path / override_path
                model_type = submodel_type
                submodel_type = None
                model_class = MODEL_CLASSES[base_model][model_type]

        # TODO: path
        # TODO: is it accurate to use path as id
        dst_convert_path = self._get_model_cache_path(model_path)

        model_path = model_class.convert_if_required(
            base_model=base_model,
            model_path=str(model_path), # TODO: refactor str/Path types logic
            output_path=dst_convert_path,
            config=model_config,
        )

        model_context = self.cache.get_model(
            model_path=model_path,
            model_class=model_class,
            base_model=base_model,
            model_type=model_type,
            submodel=submodel_type,
        )

        if model_key not in self.cache_keys:
            self.cache_keys[model_key] = set()
        self.cache_keys[model_key].add(model_context.key)

        model_hash = "<NO_HASH>" # TODO:
            
        return ModelInfo(
            context = model_context,
            name = model_name,
            base_model = base_model,
            type = submodel_type or model_type,
            hash = model_hash,
            location = model_path, # TODO:
            precision = self.cache.precision,
            _cache = self.cache,
        )

    def model_info(
        self,
        model_name: str,
        base_model: BaseModelType,
        model_type: ModelType,
    ) -> dict:
        """
        Given a model name returns the OmegaConf (dict-like) object describing it.
        """
        model_key = self.create_key(model_name, base_model, model_type)
        if model_key in self.models:
            return self.models[model_key].dict(exclude_defaults=True)
        else:
            return None # TODO: None or empty dict on not found

    def model_names(self) -> List[Tuple[str, BaseModelType, ModelType]]:
        """
        Return a list of (str, BaseModelType, ModelType) corresponding to all models 
        known to the configuration.
        """
        return [(self.parse_key(x)) for x in self.models.keys()]

    def list_model(
            self,
            model_name: str,
            base_model: BaseModelType,
            model_type: ModelType,
    ) -> dict:
        """
        Returns a dict describing one installed model, using
        the combined format of the list_models() method.
        """
        models = self.list_models(base_model,model_type,model_name)
        return models[0] if models else None

    def list_models(
        self,
        base_model: Optional[BaseModelType] = None,
        model_type: Optional[ModelType] = None,
        model_name: Optional[str] = None,
    ) -> list[dict]:
        """
        Return a list of models.
        """

        model_keys = [self.create_key(model_name, base_model, model_type)] if model_name else sorted(self.models, key=str.casefold)
        models = []
        for model_key in model_keys:
            model_config = self.models[model_key]

            cur_model_name, cur_base_model, cur_model_type = self.parse_key(model_key)
            if base_model is not None and cur_base_model != base_model:
                continue
            if model_type is not None and cur_model_type != model_type:
                continue

            model_dict = dict(
                **model_config.dict(exclude_defaults=True),
                # OpenAPIModelInfoBase
                name=cur_model_name,
                base_model=cur_base_model,
                type=cur_model_type,
            )

            models.append(model_dict)

        return models

    def print_models(self) -> None:
        """
        Print a table of models and their descriptions. This needs to be redone
        """
        # TODO: redo
        for model_type, model_dict in self.list_models().items():
            for model_name, model_info in model_dict.items():
                line = f'{model_info["name"]:25s} {model_info["type"]:10s} {model_info["description"]}'
                print(line)

    # Tested - LS
    def del_model(
        self,
        model_name: str,
        base_model: BaseModelType,
        model_type: ModelType,
    ):
        """
        Delete the named model.
        """
        model_key = self.create_key(model_name, base_model, model_type)
        model_cfg = self.models.pop(model_key, None)

        if model_cfg is None:
            raise KeyError(f"Unknown model {model_key}")

        # note: it not garantie to release memory(model can has other references)
        cache_ids = self.cache_keys.pop(model_key, [])
        for cache_id in cache_ids:
            self.cache.uncache_model(cache_id)

        # if model inside invoke models folder - delete files
        model_path = self.app_config.root_path / model_cfg.path
        cache_path = self._get_model_cache_path(model_path)
        if cache_path.exists():
            rmtree(str(cache_path))

        if model_path.is_relative_to(self.app_config.models_path):
            if model_path.is_dir():
                rmtree(str(model_path))
            else:
                model_path.unlink()

    # LS: tested
    def add_model(
        self,
        model_name: str,
        base_model: BaseModelType,
        model_type: ModelType,
        model_attributes: dict,
        clobber: bool = False,
    ) -> AddModelResult:
        """
        Update the named model with a dictionary of attributes. Will fail with an
        assertion error if the name already exists. Pass clobber=True to overwrite.
        On a successful update, the config will be changed in memory and the
        method will return True. Will fail with an assertion error if provided
        attributes are incorrect or the model name is missing.

        The returned dict has the same format as the dict returned by
        model_info().
        """

        model_class = MODEL_CLASSES[base_model][model_type]
        model_config = model_class.create_config(**model_attributes)
        model_key = self.create_key(model_name, base_model, model_type)

        if  model_key in self.models and not clobber:
            raise Exception(f'Attempt to overwrite existing model definition "{model_key}"')

        old_model = self.models.pop(model_key, None)
        if old_model is not None:
            # TODO: if path changed and old_model.path inside models folder should we delete this too?

            # remove conversion cache as config changed
            old_model_path = self.app_config.root_path / old_model.path
            old_model_cache = self._get_model_cache_path(old_model_path)
            if old_model_cache.exists():
                if old_model_cache.is_dir():
                    rmtree(str(old_model_cache))
                else:
                    old_model_cache.unlink()

            # remove in-memory cache
            # note: it not guaranteed to release memory(model can has other references)
            cache_ids = self.cache_keys.pop(model_key, [])
            for cache_id in cache_ids:
                self.cache.uncache_model(cache_id)

        self.models[model_key] = model_config
        self.commit()
        return AddModelResult(
            name = model_name,
            model_type = model_type,
            base_model = base_model,
            config = model_config,
        )

    def convert_model (
            self,
            model_name: str,
            base_model: BaseModelType,
            model_type: Union[ModelType.Main,ModelType.Vae],
    ) -> AddModelResult:
        '''
        Convert a checkpoint file into a diffusers folder, deleting the cached
        version and deleting the original checkpoint file if it is in the models
        directory.
        :param model_name: Name of the model to convert
        :param base_model: Base model type
        :param model_type: Type of model ['vae' or 'main']

        This will raise a ValueError unless the model is a checkpoint.
        '''
        info = self.model_info(model_name, base_model, model_type)
        if info["model_format"] != "checkpoint":
            raise ValueError(f"not a checkpoint format model: {model_name}")

        # We are taking advantage of a side effect of get_model() that converts check points
        # into cached diffusers directories stored at `location`. It doesn't matter
        # what submodeltype we request here, so we get the smallest.
        submodel = {"submodel_type": SubModelType.Tokenizer} if model_type==ModelType.Main else {}
        model = self.get_model(model_name,
                               base_model,
                               model_type,
                               **submodel,
                               )
        checkpoint_path = self.app_config.root_path / info["path"]
        old_diffusers_path = self.app_config.models_path / model.location
        new_diffusers_path = self.app_config.models_path / base_model.value / model_type.value / model_name
        if new_diffusers_path.exists():
            raise ValueError(f"A diffusers model already exists at {new_diffusers_path}")

        try:
            move(old_diffusers_path,new_diffusers_path)
            info["model_format"] = "diffusers"
            info["path"] = str(new_diffusers_path.relative_to(self.app_config.root_path))
            info.pop('config')

            result = self.add_model(model_name, base_model, model_type,
                                    model_attributes = info,
                                    clobber=True)
        except:
            # something went wrong, so don't leave dangling diffusers model in directory or it will cause a duplicate model error!
            rmtree(new_diffusers_path)
            raise
        
        if checkpoint_path.exists() and checkpoint_path.is_relative_to(self.app_config.models_path):
            checkpoint_path.unlink()
        
        return result
    
    def search_models(self, search_folder):
        self.logger.info(f"Finding Models In: {search_folder}")
        models_folder_ckpt = Path(search_folder).glob("**/*.ckpt")
        models_folder_safetensors = Path(search_folder).glob("**/*.safetensors")

        ckpt_files = [x for x in models_folder_ckpt if x.is_file()]
        safetensor_files = [x for x in models_folder_safetensors if x.is_file()]

        files = ckpt_files + safetensor_files

        found_models = []
        for file in files:
            location = str(file.resolve()).replace("\\", "/")
            if (
                "model.safetensors" not in location
                and "diffusion_pytorch_model.safetensors" not in location
            ):
                found_models.append({"name": file.stem, "location": location})

        return search_folder, found_models

    def commit(self, conf_file: Path=None) -> None:
        """
        Write current configuration out to the indicated file.
        """
        data_to_save = dict()
        data_to_save["__metadata__"] = self.config_meta.dict()

        for model_key, model_config in self.models.items():
            model_name, base_model, model_type = self.parse_key(model_key)
            model_class = MODEL_CLASSES[base_model][model_type]
            if model_class.save_to_config:
                # TODO: or exclude_unset better fits here?
                data_to_save[model_key] = model_config.dict(exclude_defaults=True, exclude={"error"})
                # alias for config file
                data_to_save[model_key]["format"] = data_to_save[model_key].pop("model_format")

        yaml_str = OmegaConf.to_yaml(data_to_save)
        config_file_path = conf_file or self.config_path
        assert config_file_path is not None,'no config file path to write to'
        config_file_path = self.app_config.root_path / config_file_path
        tmpfile = os.path.join(os.path.dirname(config_file_path), "new_config.tmp")
        with open(tmpfile, "w", encoding="utf-8") as outfile:
            outfile.write(self.preamble())
            outfile.write(yaml_str)
        os.replace(tmpfile, config_file_path)

    def preamble(self) -> str:
        """
        Returns the preamble for the config file.
        """
        return textwrap.dedent(
            """\
            # This file describes the alternative machine learning models
            # available to InvokeAI script.
            #
            # To add a new model, follow the examples below. Each
            # model requires a model config file, a weights file,
            # and the width and height of the images it
            # was trained on.
        """
        )

    def scan_models_directory(
        self,
        base_model: Optional[BaseModelType] = None,
        model_type: Optional[ModelType] = None,
    ):

        loaded_files = set()
        new_models_found = False

        self.logger.info(f'scanning {self.app_config.models_path} for new models')
        with Chdir(self.app_config.root_path):
            for model_key, model_config in list(self.models.items()):
                model_name, cur_base_model, cur_model_type = self.parse_key(model_key)
                model_path = self.app_config.root_path.absolute() / model_config.path
                if not model_path.exists():
                    model_class = MODEL_CLASSES[cur_base_model][cur_model_type]
                    if model_class.save_to_config:
                        model_config.error = ModelError.NotFound
                    else:
                        self.models.pop(model_key, None)
                else:
                    loaded_files.add(model_path)

            for cur_base_model in BaseModelType:
                if base_model is not None and cur_base_model != base_model:
                    continue

                for cur_model_type in ModelType:
                    if model_type is not None and cur_model_type != model_type:
                        continue
                    model_class = MODEL_CLASSES[cur_base_model][cur_model_type]
                    models_dir = self.app_config.models_path / cur_base_model.value / cur_model_type.value

                    if not models_dir.exists():
                        continue # TODO: or create all folders?

                    for model_path in models_dir.iterdir():
                        if model_path not in loaded_files: # TODO: check
                            model_name = model_path.name if model_path.is_dir() else model_path.stem
                            model_key = self.create_key(model_name, cur_base_model, cur_model_type)

                            if model_key in self.models:
                                raise Exception(f"Model with key {model_key} added twice")

                            if model_path.is_relative_to(self.app_config.root_path):
                                model_path = model_path.relative_to(self.app_config.root_path)
                            try:
                                model_config: ModelConfigBase = model_class.probe_config(str(model_path))
                                self.models[model_key] = model_config
                                new_models_found = True
                            except NotImplementedError as e:
                                self.logger.warning(e)

        imported_models = self.autoimport()

        if (new_models_found or imported_models) and self.config_path:
            self.commit()

    def autoimport(self)->Dict[str, AddModelResult]:
        '''
        Scan the autoimport directory (if defined) and import new models, delete defunct models.
        '''
        # avoid circular import
        from invokeai.backend.install.model_install_backend import ModelInstall
        from invokeai.frontend.install.model_install import ask_user_for_prediction_type
        
        installer = ModelInstall(config = self.app_config,
                                 model_manager = self,
                                 prediction_type_helper = ask_user_for_prediction_type,
                                 )
        
        scanned_dirs = set()
        
        config = self.app_config
        known_paths = {(self.app_config.root_path / x['path']) for x in self.list_models()}

        for autodir in [config.autoimport_dir,
                        config.lora_dir,
                        config.embedding_dir,
                        config.controlnet_dir]:
            if autodir is None:
                continue

            self.logger.info(f'Scanning {autodir} for models to import')
            installed = dict()
        
            autodir = self.app_config.root_path / autodir
            if not autodir.exists():
                continue

            items_scanned = 0
            new_models_found = dict()
            
            for root, dirs, files in os.walk(autodir):
                items_scanned += len(dirs) + len(files)
                for d in dirs:
                    path = Path(root) / d
                    if path in known_paths or path.parent in scanned_dirs:
                        scanned_dirs.add(path)
                        continue
                    if any([(path/x).exists() for x in {'config.json','model_index.json','learned_embeds.bin','pytorch_lora_weights.bin'}]):
                        new_models_found.update(installer.heuristic_import(path))
                        scanned_dirs.add(path)

                for f in files:
                    path = Path(root) / f
                    if path in known_paths or path.parent in scanned_dirs:
                        continue
                    if path.suffix in {'.ckpt','.bin','.pth','.safetensors','.pt'}:
                        import_result = installer.heuristic_import(path)
                        new_models_found.update(import_result)

            self.logger.info(f'Scanned {items_scanned} files and directories, imported {len(new_models_found)} models')
            installed.update(new_models_found)

        return installed

    def heuristic_import(self,
                         items_to_import: Set[str],
                         prediction_type_helper: Callable[[Path],SchedulerPredictionType]=None,
                         )->Dict[str, AddModelResult]:
        '''Import a list of paths, repo_ids or URLs. Returns the set of
        successfully imported items.
        :param items_to_import: Set of strings corresponding to models to be imported.
        :param prediction_type_helper: A callback that receives the Path of a Stable Diffusion 2 checkpoint model and returns a SchedulerPredictionType.

        The prediction type helper is necessary to distinguish between
        models based on Stable Diffusion 2 Base (requiring
        SchedulerPredictionType.Epsilson) and Stable Diffusion 768
        (requiring SchedulerPredictionType.VPrediction). It is
        generally impossible to do this programmatically, so the
        prediction_type_helper usually asks the user to choose.

        The result is a set of successfully installed models. Each element
        of the set is a dict corresponding to the newly-created OmegaConf stanza for
        that model.

        May return the following exceptions:
        - KeyError   - one or more of the items to import is not a valid path, repo_id or URL
        - ValueError - a corresponding model already exists
        '''
        # avoid circular import here
        from invokeai.backend.install.model_install_backend import ModelInstall
        successfully_installed = dict()
        
        installer = ModelInstall(config = self.app_config,
                                 prediction_type_helper = prediction_type_helper,
                                 model_manager = self)
        for thing in items_to_import:
            installed = installer.heuristic_import(thing)
            successfully_installed.update(installed)
        self.commit()                
        return successfully_installed
