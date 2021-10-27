import unittest

import torch

from pytorch_metric_learning.distances import CosineSimilarity
from pytorch_metric_learning.losses import CentroidTripletLoss
from pytorch_metric_learning.reducers import MeanReducer
from pytorch_metric_learning.utils import common_functions as c_f

from .. import TEST_DEVICE, TEST_DTYPES


class TestCentroidTripletLoss(unittest.TestCase):
    def test_centroid_triplet_loss(self):
        margin = 0.2
        loss_funcA = CentroidTripletLoss(margin=margin)
        loss_funcB = CentroidTripletLoss(margin=margin, reducer=MeanReducer())
        loss_funcC = CentroidTripletLoss(margin=margin, distance=CosineSimilarity())
        loss_funcD = CentroidTripletLoss(
            margin=margin, reducer=MeanReducer(), distance=CosineSimilarity()
        )
        loss_funcE = CentroidTripletLoss(margin=margin, smooth_loss=True)
        
        for dtype in TEST_DTYPES:
            embedding_angles = [0, 0, 40, 40, 80, 80]
            embeddings = torch.tensor(
                [c_f.angle_to_coord(a) for a in embedding_angles],
                requires_grad=True,
                dtype=dtype,
            ).to(
                TEST_DEVICE
            )  # 2D embeddings
            true_centroids = [
                embeddings[(i*2): (i*2)+2].sum(-2) / 2
                for i in range(len(embeddings) // 2)
            ]

            labels = torch.LongTensor([0, 0, 1, 1, 2, 2])

            [lossA, lossB, lossC, lossD, lossE] = [
                x(embeddings, labels)
                for x in [loss_funcA, loss_funcB, loss_funcC, loss_funcD, loss_funcE]
            ]

            triplets = [
                (0, 1, 2),
                (0, 1, 3),
                (0, 1, 4),
                (0, 1, 5),

                (1, 0, 2),
                (1, 0, 3),
                (1, 0, 4),
                (1, 0, 5),

                (2, 3, 0),
                (2, 3, 1),
                (2, 3, 4),
                (2, 3, 5),

                (3, 2, 0),
                (3, 2, 1),
                (3, 2, 4),
                (3, 2, 5)
            ]
            print("embeddings", embeddings)
            print("true_centroids", true_centroids)
            correct_loss = 0
            correct_loss_cosine = 0
            correct_smooth_loss = 0
            num_non_zero_triplets = 0
            num_non_zero_triplets_cosine = 0
            for a, p, n in triplets:
                anchor = embeddings[a]
                positive = true_centroids[p // 2]
                negative = true_centroids[n // 2]

                ap_dist = torch.sqrt(torch.sum((anchor - positive) ** 2))
                an_dist = torch.sqrt(torch.sum((anchor - negative) ** 2))
                curr_loss = torch.relu(ap_dist - an_dist + margin)
                
                curr_loss_cosine = torch.relu(
                    torch.sum(anchor * negative) - torch.sum(anchor * positive) + margin
                )
                correct_smooth_loss += torch.nn.functional.softplus(
                    ap_dist - an_dist + margin
                )
                if curr_loss > 0:
                    num_non_zero_triplets += 1
                if curr_loss_cosine > 0:
                    num_non_zero_triplets_cosine += 1
                correct_loss += curr_loss
                correct_loss_cosine += curr_loss_cosine
            rtol = 1e-2 if dtype == torch.float16 else 1e-5

            print("lossA", lossA)
            print("correct_loss", correct_loss)
            print("num_non_zero_triplets", num_non_zero_triplets)
            print("lossE", lossE)
            print("correct_smooth_loss / len(triplets)", correct_smooth_loss / len(triplets))
            # self.assertTrue(
            #     torch.isclose(lossA, correct_loss / num_non_zero_triplets, rtol=rtol)
            # )
            self.assertTrue(
                torch.isclose(lossB, correct_loss / len(triplets), rtol=rtol)
            )
            # self.assertTrue(
            #     torch.isclose(
            #         lossC, correct_loss_cosine / num_non_zero_triplets_cosine, rtol=rtol
            #     )
            # )
            self.assertTrue(
                torch.isclose(lossD, correct_loss_cosine / len(triplets), rtol=rtol)
            )
            self.assertTrue(
                torch.isclose(lossE, correct_smooth_loss / len(triplets), rtol=rtol)
            )

    def test_with_no_valid_triplets_no_imbalance(self):
        loss_funcA = CentroidTripletLoss(margin=0.2)
        loss_funcB = CentroidTripletLoss(margin=0.2, reducer=MeanReducer())
        for dtype in TEST_DTYPES:
            embedding_angles = [0, 20, 40, 60, 80]
            embeddings = torch.tensor(
                [c_f.angle_to_coord(a) for a in embedding_angles],
                requires_grad=True,
                dtype=dtype,
            ).to(
                TEST_DEVICE
            )  # 2D embeddings
            labels = torch.LongTensor([0, 1, 2, 3, 4])

            lossA = loss_funcA(embeddings, labels)
            lossB = loss_funcB(embeddings, labels)
            self.assertEqual(lossA, 0)
            self.assertEqual(lossB, 0)

    def test_backward(self):
        margin = 0.2
        loss_funcA = CentroidTripletLoss(margin=margin)
        loss_funcB = CentroidTripletLoss(margin=margin, reducer=MeanReducer())
        loss_funcC = CentroidTripletLoss(smooth_loss=True)
        for dtype in TEST_DTYPES:
            for loss_func in [loss_funcA, loss_funcB, loss_funcC]:
                embedding_angles = [0, 20, 40, 60, 80]
                embeddings = torch.tensor(
                    [c_f.angle_to_coord(a) for a in embedding_angles],
                    requires_grad=True,
                    dtype=dtype,
                ).to(
                    TEST_DEVICE
                )  # 2D embeddings
                labels = torch.LongTensor([0, 0, 1, 1, 2])

                loss = loss_func(embeddings, labels)
                loss.backward()
