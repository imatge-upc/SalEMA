import cv2
import os
import datetime
import numpy as np
from model import SalGANmore, SalGAN_EMA
import pickle
import torch
from torchvision import transforms, utils
import torch.backends.cudnn as cudnn
from torch import nn
from torch.utils import data
from torch.autograd import Variable
from data_loader import DHF1K_frames, Ego_frames, Hollywood_frames

dtype = torch.FloatTensor
if torch.cuda.is_available():
    dtype = torch.cuda.FloatTensor
"""
Before inferring check:
EMA_LOC,
RESIDUAL,
pretrained_model,
dst
"""
dataset_name = "Hollywood-2"
dataset_name = "DHF1K"
clip_length = 10 #with 10 clips the loss seems to reach zero very fast
STARTING_VIDEO = 601
NUMBER_OF_VIDEOS = 700# DHF1K offers 700 labeled videos, the other 300 are held back by the authors
EMA_LOC = 30     # 30 is the bottleneck
#EMA_LOC_2 = 54
RESIDUAL = False
DOUBLE = False
DROPOUT = True
ALPHA = 0.1
#pretrained_model = '/imatge/lpanagiotis/work/SalGANmore/src/model_weights/gen_model.pt' # Vanilla SalGAN
#pretrained_model = './SalGAN.pt'
#pretrained_model = 'model_weights/salgan_salicon.pt' #JuanJo's weights, set EMA_LOC to None for original SalBCE, otherwise EMA will be added
#pretrained_model = './SalGANplus.pt'
pretrained_model = './SalGANmid.pt' #SalGANmid stands for SalCLSTM30
pretrained_model = './SalEMA{}D_H.pt'.format(EMA_LOC)
#pretrained_model = 'SalEMA{}&{}.pt'.format(EMA_LOC,EMA_LOC_2)
frame_size = (192, 256)
# Destination for predictions:
dst = "/home/linardos/Hollywood-2/testing"
dst = "/imatge/lpanagiotis/work/{}/{}a{}_predictions".format(dataset_name, pretrained_model.replace(".pt", ""), ALPHA)
#dst = "/imatge/lpanagiotis/work/{}/SG_predictions".format(dataset_name)
frames_path = "/imatge/lpanagiotis/work/DHF1K/frames"
gt_path = "/imatge/lpanagiotis/work/DHF1K/maps"

params = {'batch_size': 1,
          'num_workers': 4,
          'pin_memory': True}

def main(dataset_name=dataset_name):

    # =================================================
    # ================ Data Loading ===================

    #Expect Error if either validation size or train size is 1
    if dataset_name == "DHF1K":
        print("Commencing inference for dataset {}".format(dataset_name))
        dataset = DHF1K_frames(
            frames_path = frames_path,
            gt_path = gt_path,
            starting_video = STARTING_VIDEO,
            number_of_videos = NUMBER_OF_VIDEOS,
            clip_length = clip_length,
            split = None,
            resolution = frame_size)
             #add a parameter node = training or validation

    elif dataset_name == "Egomon":
        print("Commencing inference for dataset {}".format(dataset_name))
        dataset = Ego_frames(
            frames_path = frames_path,
            clip_length = clip_length,
            resolution = frame_size)
        activity = dataset.match_i_to_act

    elif dataset_name == "Hollywood-2":
        print("Commencing inference for dataset {}".format(dataset_name))
        dataset = Hollywood_frames(
            root_path = dst,
            clip_length = clip_length,
            resolution = frame_size)
        video_name_list = dataset.video_names() #match an index to the sample video name

    print("Size of test set is {}".format(len(dataset)))

    loader = data.DataLoader(dataset, **params)

    # =================================================
    # ================= Load Model ====================

    # Using same kernel size as they do in the DHF1K paper
    # Amaia uses default hidden size 128
    # input size is 1 since we have grayscale images
    if pretrained_model == './SalGANplus.pt':

        model = SalGANmore.SalGANplus(seed_init=65, freeze=False)

        temp = torch.load(pretrained_model)['state_dict']
        # Because of dataparallel there is contradiction in the name of the keys so we need to remove part of the string in the keys:.
        from collections import OrderedDict
        checkpoint = OrderedDict()
        for key in temp.keys():
            new_key = key.replace("module.","")
            checkpoint[new_key]=temp[key]

        model.load_state_dict(checkpoint, strict=True)
        print("Pre-trained model SalGANplus loaded succesfully")

        TEMPORAL = True

    elif pretrained_model == './SalGANmid.pt':

        model = SalGANmore.SalGANmid(seed_init=65, freeze=False, residual=False)

        temp = torch.load(pretrained_model)['state_dict']
        # Because of dataparallel there is contradiction in the name of the keys so we need to remove part of the string in the keys:.
        from collections import OrderedDict
        checkpoint = OrderedDict()
        for key in temp.keys():
            new_key = key.replace("module.","")
            checkpoint[new_key]=temp[key]

        model.load_state_dict(checkpoint, strict=True)
        print("Pre-trained model SalGANmid loaded succesfully")

        TEMPORAL = True

    elif pretrained_model == './SalGAN.pt':

        model = SalGANmore.SalGAN()

        temp = torch.load(pretrained_model)['state_dict']
        # Because of dataparallel there is contradiction in the name of the keys so we need to remove part of the string in the keys:.
        from collections import OrderedDict
        checkpoint = OrderedDict()
        for key in temp.keys():
            new_key = key.replace("module.","")
            checkpoint[new_key]=temp[key]

        model.load_state_dict(checkpoint, strict=True)
        print("Pre-trained model tuned SalGAN loaded succesfully")

        TEMPORAL = False

    elif "EMA" in pretrained_model:
        if DOUBLE:
            model = SalGAN_EMA.SalGAN_EMA2(alpha=ALPHA, ema_loc_1=EMA_LOC, ema_loc_2=EMA_LOC_2)
        else:
            model = SalGAN_EMA.SalGAN_EMA(alpha=ALPHA, residual=RESIDUAL, dropout = DROPOUT, ema_loc=EMA_LOC)

        temp = torch.load(pretrained_model)['state_dict']
        # Because of dataparallel there is contradiction in the name of the keys so we need to remove part of the string in the keys:.
        from collections import OrderedDict
        checkpoint = OrderedDict()
        for key in temp.keys():
            new_key = key.replace("module.","")
            checkpoint[new_key]=temp[key]

        model.load_state_dict(checkpoint, strict=True)
        print("Pre-trained model {} loaded succesfully".format(pretrained_model))
        if RESIDUAL:
            print("Residual connection is included.")

        TEMPORAL = True

    elif pretrained_model == 'model_weights/salgan_salicon.pt':

        if EMA_LOC == None:
            model = SalGANmore.SalGAN()
            TEMPORAL = False
            print("Pre-trained model SalBCE loaded succesfully.")
        else:
            model = SalGAN_EMA.SalGAN_EMA(alpha=ALPHA, ema_loc=EMA_LOC)
            TEMPORAL = True
            print("Pre-trained model SalBCE loaded succesfully. EMA inference will commence soon.")

        model.salgan.load_state_dict(torch.load(pretrained_model)['state_dict'])


    elif pretrained_model == '/imatge/lpanagiotis/work/SalGANmore/src/model_weights/gen_model.pt':
        model = SalGANmore.SalGAN()
        model.salgan.load_state_dict(torch.load(pretrained_model))
        print("Pre-trained model vanilla SalGAN loaded succesfully")

        TEMPORAL = False
    else:
        print("Your model was not recognized, check the name of the model and try again.")
        exit()

    #model = nn.DataParallel(model).cuda()
    if torch.cuda.is_available():
        cudnn.benchmark = True #https://discuss.pytorch.org/t/what-does-torch-backends-cudnn-benchmark-do/5936
        model = model.cuda()

    # ==================================================
    # ================== Inference =====================

    if not os.path.exists(dst):
        os.mkdir(dst)
    else:
        print("Be warned, you are about to write on an existing folder {}. If this is not intentional cancel now.".format(dst))

    # switch to evaluate mode
    model.eval()

    for i, video in enumerate(loader):

        count = 0
        state = None # Initially no hidden state

        if dataset_name == "DHF1K":

            video_dst = os.path.join(dst, str(STARTING_VIDEO+i).zfill(4))
            if not os.path.exists(video_dst):
                os.mkdir(video_dst)

            for j, (clip, _) in enumerate(video):
                clip = Variable(clip.type(dtype).transpose(0,1), requires_grad=False)
                if DOUBLE:
                    if state == None:
                        state = (None, None)
                    for idx in range(clip.size()[0]):
                        # Compute output
                        state, saliency_map = model.forward(input_ = clip[idx], prev_state_1 = state[0], prev_state_2 = state[1])

                        saliency_map = saliency_map.squeeze(0) # Target is 3 dimensional (grayscale image)

                        post_process_saliency_map = (saliency_map-torch.min(saliency_map))/(torch.max(saliency_map)-torch.min(saliency_map))
                        utils.save_image(post_process_saliency_map, os.path.join(video_dst, "{}.png".format(str(count).zfill(4))))

                else:
                    for idx in range(clip.size()[0]):
                        # Compute output
                        if TEMPORAL:
                            state, saliency_map = model.forward(input_ = clip[idx], prev_state = state)
                        else:
                            saliency_map = model.forward(input_ = clip[idx])

                        count+=1
                        saliency_map = saliency_map.squeeze(0)

                        post_process_saliency_map = (saliency_map-torch.min(saliency_map))/(torch.max(saliency_map)-torch.min(saliency_map))
                        utils.save_image(post_process_saliency_map, os.path.join(video_dst, "{}.png".format(str(count).zfill(4))))

                if TEMPORAL:
                    state = repackage_hidden(state)

        elif dataset_name == "Hollywood-2":

            video_dst = os.path.join(dst, video_name_list[i], '{}_predictions'.format(pretrained_model.replace(".pt", "")))
            print("Destination: {}".format(video_dst))
            if not os.path.exists(video_dst):
                os.mkdir(video_dst)

            for j, (clip, _) in enumerate(video):
                clip = Variable(clip.type(dtype).transpose(0,1), requires_grad=False)
                if DOUBLE:
                    if state == None:
                        state = (None, None)
                    for idx in range(clip.size()[0]):
                        # Compute output
                        state, saliency_map = model.forward(input_ = clip[idx], prev_state_1 = state[0], prev_state_2 = state[1])

                        saliency_map = saliency_map.squeeze(0) # Target is 3 dimensional (grayscale image)

                        post_process_saliency_map = (saliency_map-torch.min(saliency_map))/(torch.max(saliency_map)-torch.min(saliency_map))
                        utils.save_image(post_process_saliency_map, os.path.join(video_dst, "{}.png".format(str(count).zfill(4))))

                else:
                    for idx in range(clip.size()[0]):
                        # Compute output
                        if TEMPORAL:
                            state, saliency_map = model.forward(input_ = clip[idx], prev_state = state)
                        else:
                            saliency_map = model.forward(input_ = clip[idx])

                        count+=1
                        saliency_map = saliency_map.squeeze(0)

                        post_process_saliency_map = (saliency_map-torch.min(saliency_map))/(torch.max(saliency_map)-torch.min(saliency_map))
                        utils.save_image(post_process_saliency_map, os.path.join(video_dst, "{}{}.png".format(video_name_list[i][:-1], str(count).zfill(5))))
                        if count == 1:
                            print("The final destination is {}. Cancel now if this is incorrect".format(os.path.join(video_dst, "{}{}.png".format(video_name_list[i][:-1], str(count).zfill(5)))))

                if TEMPORAL:
                    state = repackage_hidden(state)
        elif dataset_name == "Egomon":

            video_dst = os.path.join(dst, activity[i])
            if not os.path.exists(video_dst):
                os.mkdir(video_dst)

            for j, (frame_names, clip) in enumerate(video):
                clip = Variable(clip.type(dtype).transpose(0,1), requires_grad=False)
                for idx in range(clip.size()[0]):
                    # Compute output

                    if TEMPORAL:
                        state, saliency_map = model.forward(input_ = clip[idx], prev_state = state)
                    else:
                        saliency_map = model.forward(input_ = clip[idx])

                    count+=1
                    saliency_map = saliency_map.squeeze(0)

                    post_process_saliency_map = (saliency_map-torch.min(saliency_map))/(torch.max(saliency_map)-torch.min(saliency_map))
                    utils.save_image(post_process_saliency_map, os.path.join(video_dst, frame_names[idx][0]))



                if TEMPORAL:
                    state = repackage_hidden(state)


        print("Video {} done".format(i+STARTING_VIDEO))

def repackage_hidden(h):
    """Wraps hidden states in new Tensors, to detach them from their history."""
    if isinstance(h, torch.Tensor):
        return h.detach()
    else:
        return tuple(repackage_hidden(v) for v in h)

if __name__ == '__main__':
    main()
