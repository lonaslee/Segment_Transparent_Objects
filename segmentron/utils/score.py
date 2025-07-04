"""Evaluation Metrics for Semantic Segmentation"""
import torch
import numpy as np
from torch import distributed as dist
import copy
from IPython import embed

__all__ = ['SegmentationMetric', 'batch_pix_accuracy', 'batch_intersection_union',
           'pixelAccuracy', 'intersectionAndUnion', 'hist_info', 'compute_score']


class SegmentationMetric(object):
    """Computes pixAcc and mIoU metric scores
    """

    def __init__(self, nclass, distributed, num_gpu):
        super(SegmentationMetric, self).__init__()
        self.nclass = nclass
        self.distributed = distributed
        self.num_gpu = num_gpu
        self.reset()

    def update(self, preds, labels):
        """Updates the internal evaluation result.

        Parameters
        ----------
        labels : 'NumpyArray' or list of `NumpyArray`
            The labels of the data.
        preds : 'NumpyArray' or list of `NumpyArray`
            Predicted values.
        """

        def reduce_tensor(tensor):
            if isinstance(tensor, torch.Tensor):
                rt = tensor.clone()
            else:
                rt = copy.deepcopy(tensor)
            dist.all_reduce(rt, op=dist.ReduceOp.SUM)
            return rt

        def evaluate_worker(self, pred, label):

            correct, labeled = batch_pix_accuracy(pred, label)
            inter, union = batch_intersection_union(pred, label, self.nclass)
            mae = batch_mae(pred, label)
            bers, bers_count = batch_ber(pred, label, self.nclass)

            if self.distributed:
                correct = reduce_tensor(correct)
                labeled = reduce_tensor(labeled)
                inter = reduce_tensor(inter.cuda())
                union = reduce_tensor(union.cuda())
                mae = reduce_tensor(mae.cuda())
                bers = reduce_tensor(bers.cuda())
                bers_count = reduce_tensor((bers_count.cuda()))

            torch.cuda.synchronize()
            self.total_correct += correct.item()
            self.total_label += labeled.item()

            if self.total_inter.device != inter.device:
                self.total_inter = self.total_inter.to(inter.device)
                self.total_union = self.total_union.to(union.device)
            self.total_inter += inter
            self.total_union += union

            self.total_mae.append(mae)

            if self.total_bers.device != bers.device:
                self.total_bers = self.total_bers.to(bers.device)
                self.total_bers_count = self.total_bers_count.to(bers_count.device)
            self.total_bers += bers
            self.total_bers_count += bers_count

        if isinstance(preds, torch.Tensor):
            evaluate_worker(self, preds, labels)
        elif isinstance(preds, (list, tuple)):
            for (pred, label) in zip(preds, labels):
                evaluate_worker(self, pred, label)

    def get(self, return_category_iou=False):
        """Gets the current evaluation result.

        Returns
        -------
        metrics : tuple of float
            pixAcc and mIoU
        """
        pixAcc = 1.0 * self.total_correct / (2.220446049250313e-16 + self.total_label)  # remove np.spacing(1)
        IoU = 1.0 * self.total_inter / (2.220446049250313e-16 + self.total_union)
        # mIoU = IoU.mean().item()
        mIoU = IoU[1: ].mean().item()
        mae = 1.0 * torch.Tensor(self.total_mae).mean().item() / self.num_gpu

        Ber = 1.0 * self.total_bers / self.total_bers_count
        mBer = Ber[1: ].mean().item()

        if return_category_iou:
            return pixAcc, mIoU, IoU.cpu().numpy(), mae, mBer, Ber.cpu().numpy()
        return pixAcc, mIoU, mae, mBer

    def reset(self):
        """Resets the internal evaluation result to initial state."""
        self.total_inter = torch.zeros(self.nclass)
        self.total_union = torch.zeros(self.nclass)
        self.total_correct = 0
        self.total_label = 0
        self.total_mae = []

        self.total_bers = torch.zeros(self.nclass)
        self.total_bers_count = torch.zeros(self.nclass)


def batch_pix_accuracy(output, target):
    """PixAcc"""
    # inputs are numpy array, output 4D, target 3D
    predict = torch.argmax(output.long(), 1) + 1
    target = target.long() + 1

    '''do not care background'''
    # pixel_labeled = torch.sum(target > 0)
    # pixel_correct = torch.sum((predict == target) * (target > 0))

    pixel_labeled = torch.sum(target > 1)
    pixel_correct = torch.sum((predict == target) * (target > 1))
    assert pixel_correct <= pixel_labeled, "Correct area should be smaller than Labeled"
    return pixel_correct, pixel_labeled

def batch_mae(output, target):
    """Mean Average Error"""
    # inputs are numpy array, output 4D, target 3D
    predict = (torch.argmax(output, 1)).float()
    target = target.float()

    mae = (predict - target).abs().mean()
    return mae

def batch_ber(output, target, nclass):
    predict = torch.argmax(output.long(), 1)
    target = target.long()
    bers = torch.zeros(nclass)
    bers_count = torch.zeros(nclass)
    bers_count[0] = 1

    for class_id in range(1, nclass):
        valid = target == class_id
        if valid.sum() == 0:
            continue
        N_p = torch.sum(target == class_id)
        N_n = torch.sum(target != class_id)
        TP = torch.sum((predict == target) * valid)
        TN = torch.sum((predict == target) * (1 - valid.float()))

        N_p = N_p.float(); N_n = N_n.float(); TP = TP.float(); TN = TN.float()
        ber = 1 - 1/2 * (TP / N_p + TN / N_n)
        ber = ber * 100

        bers[class_id] = ber
        bers_count[class_id] = 1.0

    return bers, bers_count

def batch_intersection_union(output, target, nclass):
    """mIoU"""
    # inputs are numpy array, output 4D, target 3D
    mini = 1
    maxi = nclass
    nbins = nclass
    predict = torch.argmax(output, 1) + 1
    target = target.float() + 1

    predict = predict.float() * (target > 0).float()
    intersection = predict * (predict == target).float()
    # areas of intersection and union
    # element 0 in intersection occur the main difference from np.bincount. set boundary to -1 is necessary.
    area_inter = torch.histc(intersection.cpu(), bins=nbins, min=mini, max=maxi)
    area_pred = torch.histc(predict.cpu(), bins=nbins, min=mini, max=maxi)
    area_lab = torch.histc(target.cpu(), bins=nbins, min=mini, max=maxi)
    area_union = area_pred + area_lab - area_inter
    assert torch.sum(area_inter > area_union).item() == 0, "Intersection area should be smaller than Union area"
    return area_inter.float(), area_union.float()


def pixelAccuracy(imPred, imLab):
    """
    This function takes the prediction and label of a single image, returns pixel-wise accuracy
    To compute over many images do:
    for i = range(Nimages):
         (pixel_accuracy[i], pixel_correct[i], pixel_labeled[i]) = \
            pixelAccuracy(imPred[i], imLab[i])
    mean_pixel_accuracy = 1.0 * np.sum(pixel_correct) / (np.spacing(1) + np.sum(pixel_labeled))
    """
    # Remove classes from unlabeled pixels in gt image.
    # We should not penalize detections in unlabeled portions of the image.
    # pixel_labeled = np.sum(imLab >= 0)
    # pixel_correct = np.sum((imPred == imLab) * (imLab >= 0))

    '''do not care background'''
    pixel_labeled = np.sum(imLab > 0)
    pixel_correct = np.sum((imPred == imLab) * (imLab > 0))
    pixel_accuracy = 1.0 * pixel_correct / pixel_labeled
    return (pixel_accuracy, pixel_correct, pixel_labeled)


def intersectionAndUnion(imPred, imLab, numClass):
    """
    This function takes the prediction and label of a single image,
    returns intersection and union areas for each class
    To compute over many images do:
    for i in range(Nimages):
        (area_intersection[:,i], area_union[:,i]) = intersectionAndUnion(imPred[i], imLab[i])
    IoU = 1.0 * np.sum(area_intersection, axis=1) / np.sum(np.spacing(1)+area_union, axis=1)
    """
    # Remove classes from unlabeled pixels in gt image.
    # We should not penalize detections in unlabeled portions of the image.
    imPred = imPred * (imLab >= 0)

    # Compute area intersection:
    intersection = imPred * (imPred == imLab)
    (area_intersection, _) = np.histogram(intersection, bins=numClass, range=(1, numClass))

    # Compute area union:
    (area_pred, _) = np.histogram(imPred, bins=numClass, range=(1, numClass))
    (area_lab, _) = np.histogram(imLab, bins=numClass, range=(1, numClass))
    area_union = area_pred + area_lab - area_intersection
    return (area_intersection, area_union)


def hist_info(pred, label, num_cls):
    assert pred.shape == label.shape
    k = (label >= 0) & (label < num_cls)
    labeled = np.sum(k)
    correct = np.sum((pred[k] == label[k]))

    return np.bincount(num_cls * label[k].astype(int) + pred[k], minlength=num_cls ** 2).reshape(num_cls,
                                                                                                 num_cls), labeled, correct


def compute_score(hist, correct, labeled):
    iu = np.diag(hist) / (hist.sum(1) + hist.sum(0) - np.diag(hist))
    mean_IU = np.nanmean(iu)
    mean_IU_no_back = np.nanmean(iu[1:])
    freq = hist.sum(1) / hist.sum()
    # freq_IU = (iu[freq > 0] * freq[freq > 0]).sum()
    mean_pixel_acc = correct / labeled

    return iu, mean_IU, mean_IU_no_back, mean_pixel_acc
