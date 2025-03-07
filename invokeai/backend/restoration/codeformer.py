import os
import sys
import warnings

import numpy as np
import torch

import invokeai.backend.util.logging as logger
from invokeai.app.services.config import InvokeAIAppConfig

pretrained_model_url = (
    "https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth"
)


class CodeFormerRestoration:
    def __init__(
        self, codeformer_dir="./models/core/face_restoration/codeformer", codeformer_model_path="codeformer.pth"
    ) -> None:

        self.globals = InvokeAIAppConfig.get_config()
        codeformer_dir = self.globals.root_dir / codeformer_dir
        self.model_path = codeformer_dir / codeformer_model_path
        self.codeformer_model_exists = self.model_path.exists()

        if not self.codeformer_model_exists:
            logger.error(f"NOT FOUND: CodeFormer model not found at {self.model_path}")
        sys.path.append(os.path.abspath(codeformer_dir))

    def process(self, image, strength, device, seed=None, fidelity=0.75):
        if seed is not None:
            logger.info(f"CodeFormer - Restoring Faces for image seed:{seed}")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            warnings.filterwarnings("ignore", category=UserWarning)

            from basicsr.utils import img2tensor, tensor2img
            from basicsr.utils.download_util import load_file_from_url
            from facexlib.utils.face_restoration_helper import FaceRestoreHelper
            from PIL import Image
            from torchvision.transforms.functional import normalize

            from .codeformer_arch import CodeFormer

            cf_class = CodeFormer

            cf = cf_class(
                dim_embd=512,
                codebook_size=1024,
                n_head=8,
                n_layers=9,
                connect_list=["32", "64", "128", "256"],
            ).to(device)

            # note that this file should already be downloaded and cached at
            # this point
            checkpoint_path = load_file_from_url(
                url=pretrained_model_url,
                model_dir=os.path.abspath(os.path.dirname(self.model_path)),
                progress=True,
            )
            checkpoint = torch.load(checkpoint_path)["params_ema"]
            cf.load_state_dict(checkpoint)
            cf.eval()

            image = image.convert("RGB")
            # Codeformer expects a BGR np array; make array and flip channels
            bgr_image_array = np.array(image, dtype=np.uint8)[..., ::-1]

            face_helper = FaceRestoreHelper(
                upscale_factor=1,
                use_parse=True,
                device=device,
                model_rootpath = self.globals.model_path / 'core/face_restoration/gfpgan/weights'
            )
            face_helper.clean_all()
            face_helper.read_image(bgr_image_array)
            face_helper.get_face_landmarks_5(resize=640, eye_dist_threshold=5)
            face_helper.align_warp_face()

            for idx, cropped_face in enumerate(face_helper.cropped_faces):
                cropped_face_t = img2tensor(
                    cropped_face / 255.0, bgr2rgb=True, float32=True
                )
                normalize(
                    cropped_face_t, (0.5, 0.5, 0.5), (0.5, 0.5, 0.5), inplace=True
                )
                cropped_face_t = cropped_face_t.unsqueeze(0).to(device)

                try:
                    with torch.no_grad():
                        output = cf(cropped_face_t, w=fidelity, adain=True)[0]
                        restored_face = tensor2img(
                            output.squeeze(0), rgb2bgr=True, min_max=(-1, 1)
                        )
                    del output
                    torch.cuda.empty_cache()
                except RuntimeError as error:
                    logger.error(f"Failed inference for CodeFormer: {error}.")
                    restored_face = cropped_face

                restored_face = restored_face.astype("uint8")
                face_helper.add_restored_face(restored_face)

            face_helper.get_inverse_affine(None)

            restored_img = face_helper.paste_faces_to_input_image()

            # Flip the channels back to RGB
            res = Image.fromarray(restored_img[..., ::-1])

            if strength < 1.0:
                # Resize the image to the new image if the sizes have changed
                if restored_img.size != image.size:
                    image = image.resize(res.size)
                res = Image.blend(image, res, strength)

            cf = None

            return res
