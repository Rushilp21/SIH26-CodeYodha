"""Segmentation model stub. Owner: Dev 1. Do not pretend a trained UNet exists."""


class SegmentationModel:
    def __init__(self):
        self.classes = ("parcel", "building", "road", "land_use")
        self.trained = False

    def load(self, weights_path: str) -> None:
        raise NotImplementedError("Dev 1: load PyTorch weights")
