import { MenuItem, MenuList } from '@chakra-ui/react';
import { useAppDispatch, useAppSelector } from 'app/store/storeHooks';
import { memo, useCallback, useContext } from 'react';
import {
  FaExpand,
  FaFolder,
  FaFolderPlus,
  FaShare,
  FaTrash,
} from 'react-icons/fa';
import { ContextMenu, ContextMenuProps } from 'chakra-ui-contextmenu';
import {
  resizeAndScaleCanvas,
  setInitialCanvasImage,
} from 'features/canvas/store/canvasSlice';
import { setActiveTab } from 'features/ui/store/uiSlice';
import { useTranslation } from 'react-i18next';
import { ExternalLinkIcon } from '@chakra-ui/icons';
import { IoArrowUndoCircleOutline } from 'react-icons/io5';
import { createSelector } from '@reduxjs/toolkit';
import { useFeatureStatus } from 'features/system/hooks/useFeatureStatus';
import { useRecallParameters } from 'features/parameters/hooks/useRecallParameters';
import { initialImageSelected } from 'features/parameters/store/actions';
import { sentImageToCanvas, sentImageToImg2Img } from '../store/actions';
import { useAppToaster } from 'app/components/Toaster';
import { AddImageToBoardContext } from '../../../app/contexts/AddImageToBoardContext';
import { useRemoveImageFromBoardMutation } from 'services/api/endpoints/boardImages';
import { ImageDTO } from 'services/api/types';
import { RootState, stateSelector } from 'app/store/store';
import {
  imagesAddedToBatch,
  selectionAddedToBatch,
} from 'features/batch/store/batchSlice';
import { defaultSelectorOptions } from 'app/store/util/defaultMemoizeOptions';
import { imageToDeleteSelected } from 'features/imageDeletion/store/imageDeletionSlice';

const selector = createSelector(
  [stateSelector, (state: RootState, imageDTO: ImageDTO) => imageDTO],
  ({ gallery, batch }, imageDTO) => {
    const selectionCount = gallery.selection.length;
    const isInBatch = batch.imageNames.includes(imageDTO.image_name);

    return { selectionCount, isInBatch };
  },
  defaultSelectorOptions
);

type Props = {
  image: ImageDTO;
  children: ContextMenuProps<HTMLDivElement>['children'];
};

const ImageContextMenu = ({ image, children }: Props) => {
  const { selectionCount, isInBatch } = useAppSelector((state) =>
    selector(state, image)
  );
  const dispatch = useAppDispatch();
  const { t } = useTranslation();

  const toaster = useAppToaster();

  const isLightboxEnabled = useFeatureStatus('lightbox').isFeatureEnabled;
  const isCanvasEnabled = useFeatureStatus('unifiedCanvas').isFeatureEnabled;

  const { onClickAddToBoard } = useContext(AddImageToBoardContext);

  const handleDelete = useCallback(() => {
    if (!image) {
      return;
    }
    dispatch(imageToDeleteSelected(image));
  }, [dispatch, image]);

  const { recallBothPrompts, recallSeed, recallAllParameters } =
    useRecallParameters();

  const [removeFromBoard] = useRemoveImageFromBoardMutation();

  // Recall parameters handlers
  const handleRecallPrompt = useCallback(() => {
    recallBothPrompts(
      image.metadata?.positive_conditioning,
      image.metadata?.negative_conditioning
    );
  }, [
    image.metadata?.negative_conditioning,
    image.metadata?.positive_conditioning,
    recallBothPrompts,
  ]);

  const handleRecallSeed = useCallback(() => {
    recallSeed(image.metadata?.seed);
  }, [image, recallSeed]);

  const handleSendToImageToImage = useCallback(() => {
    dispatch(sentImageToImg2Img());
    dispatch(initialImageSelected(image));
  }, [dispatch, image]);

  // const handleRecallInitialImage = useCallback(() => {
  //   recallInitialImage(image.metadata.invokeai?.node?.image);
  // }, [image, recallInitialImage]);

  const handleSendToCanvas = () => {
    dispatch(sentImageToCanvas());
    dispatch(setInitialCanvasImage(image));
    dispatch(resizeAndScaleCanvas());
    dispatch(setActiveTab('unifiedCanvas'));

    toaster({
      title: t('toast.sentToUnifiedCanvas'),
      status: 'success',
      duration: 2500,
      isClosable: true,
    });
  };

  const handleUseAllParameters = useCallback(() => {
    recallAllParameters(image);
  }, [image, recallAllParameters]);

  const handleLightBox = () => {
    // dispatch(setCurrentImage(image));
    // dispatch(setIsLightboxOpen(true));
  };

  const handleAddToBoard = useCallback(() => {
    onClickAddToBoard(image);
  }, [image, onClickAddToBoard]);

  const handleRemoveFromBoard = useCallback(() => {
    if (!image.board_id) {
      return;
    }
    removeFromBoard({ board_id: image.board_id, image_name: image.image_name });
  }, [image.board_id, image.image_name, removeFromBoard]);

  const handleOpenInNewTab = () => {
    window.open(image.image_url, '_blank');
  };

  const handleAddSelectionToBatch = useCallback(() => {
    dispatch(selectionAddedToBatch());
  }, [dispatch]);

  const handleAddToBatch = useCallback(() => {
    dispatch(imagesAddedToBatch([image.image_name]));
  }, [dispatch, image.image_name]);

  return (
    <ContextMenu<HTMLDivElement>
      menuProps={{ size: 'sm', isLazy: true }}
      renderMenu={() => (
        <MenuList sx={{ visibility: 'visible !important' }}>
          {selectionCount === 1 ? (
            <>
              <MenuItem
                icon={<ExternalLinkIcon />}
                onClickCapture={handleOpenInNewTab}
              >
                {t('common.openInNewTab')}
              </MenuItem>
              {isLightboxEnabled && (
                <MenuItem icon={<FaExpand />} onClickCapture={handleLightBox}>
                  {t('parameters.openInViewer')}
                </MenuItem>
              )}
              <MenuItem
                icon={<IoArrowUndoCircleOutline />}
                onClickCapture={handleRecallPrompt}
                isDisabled={
                  image?.metadata?.positive_conditioning === undefined
                }
              >
                {t('parameters.usePrompt')}
              </MenuItem>

              <MenuItem
                icon={<IoArrowUndoCircleOutline />}
                onClickCapture={handleRecallSeed}
                isDisabled={image?.metadata?.seed === undefined}
              >
                {t('parameters.useSeed')}
              </MenuItem>
              {/* <MenuItem
              icon={<IoArrowUndoCircleOutline />}
              onClickCapture={handleRecallInitialImage}
              isDisabled={image?.metadata?.type !== 'img2img'}
            >
              {t('parameters.useInitImg')}
            </MenuItem> */}
              <MenuItem
                icon={<IoArrowUndoCircleOutline />}
                onClickCapture={handleUseAllParameters}
                isDisabled={
                  // what should these be
                  !['t2l', 'l2l', 'inpaint'].includes(
                    String(image?.metadata?.type)
                  )
                }
              >
                {t('parameters.useAll')}
              </MenuItem>
              <MenuItem
                icon={<FaShare />}
                onClickCapture={handleSendToImageToImage}
                id="send-to-img2img"
              >
                {t('parameters.sendToImg2Img')}
              </MenuItem>
              {isCanvasEnabled && (
                <MenuItem
                  icon={<FaShare />}
                  onClickCapture={handleSendToCanvas}
                  id="send-to-canvas"
                >
                  {t('parameters.sendToUnifiedCanvas')}
                </MenuItem>
              )}
              {/* <MenuItem
                icon={<FaFolder />}
                isDisabled={isInBatch}
                onClickCapture={handleAddToBatch}
              >
                Add to Batch
              </MenuItem> */}
              <MenuItem icon={<FaFolder />} onClickCapture={handleAddToBoard}>
                {image.board_id ? 'Change Board' : 'Add to Board'}
              </MenuItem>
              {image.board_id && (
                <MenuItem
                  icon={<FaFolder />}
                  onClickCapture={handleRemoveFromBoard}
                >
                  Remove from Board
                </MenuItem>
              )}
              <MenuItem
                sx={{ color: 'error.600', _dark: { color: 'error.300' } }}
                icon={<FaTrash />}
                onClickCapture={handleDelete}
              >
                {t('gallery.deleteImage')}
              </MenuItem>
            </>
          ) : (
            <>
              <MenuItem
                isDisabled={true}
                icon={<FaFolder />}
                onClickCapture={handleAddToBoard}
              >
                Move Selection to Board
              </MenuItem>
              {/* <MenuItem
                icon={<FaFolderPlus />}
                onClickCapture={handleAddSelectionToBatch}
              >
                Add Selection to Batch
              </MenuItem> */}
              <MenuItem
                sx={{ color: 'error.600', _dark: { color: 'error.300' } }}
                icon={<FaTrash />}
                onClickCapture={handleDelete}
              >
                Delete Selection
              </MenuItem>
            </>
          )}
        </MenuList>
      )}
    >
      {children}
    </ContextMenu>
  );
};

export default memo(ImageContextMenu);
