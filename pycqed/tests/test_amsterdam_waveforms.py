import numpy as np
from pycqed.measurement.waveform_control_CC import amsterdam_waveforms as awf


class TestAmsterdamWaveforms:
    def test_amsterdam_waveform(self):
        unitlength = 10
        rescaling = 0.7
        roofScale = 0.5

        ams_sc_base = 0.47 * rescaling
        ams_sc_step = 0.07 * rescaling * roofScale
        ams_sc = awf.ams_sc(unitlength, ams_sc_base, ams_sc_step)

        ams_bottle_base = 0.55 * rescaling
        ams_bottle_delta = 0.3 * rescaling * roofScale
        ams_bottle = awf.ams_bottle(unitlength, ams_bottle_base, ams_bottle_delta)

        ams_midup_base = 0.63 * rescaling
        ams_midup_delta = 0.25 * rescaling * roofScale
        ams_midup = awf.ams_midup(unitlength, ams_midup_base, ams_midup_delta)

        ams_bottle_base3 = 0.5 * rescaling
        ams_bottle_delta3 = 0.1 * rescaling * roofScale
        ams_bottle3 = awf.ams_bottle3(unitlength, ams_bottle_base3, ams_bottle_delta3)

        ams_bottle_base2 = 0.58 * rescaling
        ams_bottle_delta2 = 0.3 * rescaling * roofScale
        ams_bottle2 = awf.ams_bottle2(unitlength, ams_bottle_base2, ams_bottle_delta2)

        amsterdam_wf = np.concatenate(
            [
                np.zeros(10),
                ams_sc,
                ams_bottle,
                ams_midup,
                ams_bottle3,
                ams_bottle2,
                np.zeros(10),
            ]
        )

        expected_wf = [
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.329,
            0.329,
            0.329,
            0.329,
            0.329,
            0.329,
            0.329,
            0.329,
            0.329,
            0.329,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.378,
            0.378,
            0.378,
            0.378,
            0.378,
            0.378,
            0.378,
            0.378,
            0.378,
            0.378,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.427,
            0.427,
            0.427,
            0.427,
            0.427,
            0.427,
            0.427,
            0.427,
            0.427,
            0.427,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.476,
            0.476,
            0.476,
            0.476,
            0.476,
            0.476,
            0.476,
            0.476,
            0.476,
            0.476,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.4515,
            0.427,
            0.427,
            0.427,
            0.427,
            0.427,
            0.427,
            0.427,
            0.427,
            0.427,
            0.427,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.4025,
            0.378,
            0.378,
            0.378,
            0.378,
            0.378,
            0.378,
            0.378,
            0.378,
            0.378,
            0.378,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.3535,
            0.329,
            0.329,
            0.329,
            0.329,
            0.329,
            0.329,
            0.329,
            0.329,
            0.329,
            0.329,
            0.385,
            0.38500015,
            0.38500238,
            0.38501202,
            0.385038,
            0.38509278,
            0.3851924,
            0.38535644,
            0.38560808,
            0.38597402,
            0.38648456,
            0.38717354,
            0.38807838,
            0.38924005,
            0.39070308,
            0.39251558,
            0.3947292,
            0.39739918,
            0.4005843,
            0.40434691,
            0.40875294,
            0.41387184,
            0.41977667,
            0.42654403,
            0.43425409,
            0.44299057,
            0.45284076,
            0.46389552,
            0.47624928,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.49,
            0.47624928,
            0.46389552,
            0.45284076,
            0.44299057,
            0.43425409,
            0.42654403,
            0.41977667,
            0.41387184,
            0.40875294,
            0.40434691,
            0.4005843,
            0.39739918,
            0.3947292,
            0.39251558,
            0.39070308,
            0.38924005,
            0.38807838,
            0.38717354,
            0.38648456,
            0.38597402,
            0.38560808,
            0.38535644,
            0.3851924,
            0.38509278,
            0.385038,
            0.38501202,
            0.38500238,
            0.38500015,
            0.385,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.4985,
            0.50249524,
            0.50620511,
            0.50962961,
            0.51276873,
            0.51562247,
            0.51819084,
            0.52047384,
            0.52247146,
            0.52418371,
            0.52561058,
            0.52675208,
            0.5276082,
            0.52817895,
            0.52846433,
            0.52846433,
            0.52817895,
            0.5276082,
            0.52675208,
            0.52561058,
            0.52418371,
            0.52247146,
            0.52047384,
            0.51819084,
            0.51562247,
            0.51276873,
            0.50962961,
            0.50620511,
            0.50249524,
            0.4985,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.441,
            0.35,
            0.35054687,
            0.35109375,
            0.35164062,
            0.3521875,
            0.35273437,
            0.35328125,
            0.35382812,
            0.354375,
            0.35492187,
            0.35546875,
            0.35601563,
            0.3565625,
            0.35710937,
            0.35765625,
            0.35820312,
            0.35875,
            0.35929687,
            0.35984375,
            0.36039062,
            0.3609375,
            0.36148437,
            0.36203125,
            0.36257812,
            0.363125,
            0.36367187,
            0.36421875,
            0.36476562,
            0.3653125,
            0.36585937,
            0.36640625,
            0.36695312,
            0.3675,
            0.36804687,
            0.36859375,
            0.36914062,
            0.3696875,
            0.37023438,
            0.37078125,
            0.37132812,
            0.371875,
            0.37242187,
            0.37296875,
            0.37351562,
            0.3740625,
            0.37460937,
            0.37515625,
            0.37570312,
            0.37625,
            0.37679687,
            0.37734375,
            0.37789062,
            0.3784375,
            0.37898437,
            0.37953125,
            0.38007812,
            0.380625,
            0.38117187,
            0.38171875,
            0.38226562,
            0.3828125,
            0.38335937,
            0.38390625,
            0.38445312,
            0.385,
            0.385,
            0.38445312,
            0.38390625,
            0.38335937,
            0.3828125,
            0.38226562,
            0.38171875,
            0.38117187,
            0.380625,
            0.38007812,
            0.37953125,
            0.37898437,
            0.3784375,
            0.37789062,
            0.37734375,
            0.37679687,
            0.37625,
            0.37570312,
            0.37515625,
            0.37460937,
            0.3740625,
            0.37351562,
            0.37296875,
            0.37242187,
            0.371875,
            0.37132812,
            0.37078125,
            0.37023438,
            0.3696875,
            0.36914062,
            0.36859375,
            0.36804687,
            0.3675,
            0.36695312,
            0.36640625,
            0.36585937,
            0.3653125,
            0.36476562,
            0.36421875,
            0.36367187,
            0.363125,
            0.36257812,
            0.36203125,
            0.36148437,
            0.3609375,
            0.36039062,
            0.35984375,
            0.35929687,
            0.35875,
            0.35820312,
            0.35765625,
            0.35710937,
            0.3565625,
            0.35601563,
            0.35546875,
            0.35492187,
            0.354375,
            0.35382812,
            0.35328125,
            0.35273437,
            0.3521875,
            0.35164062,
            0.35109375,
            0.35054687,
            0.35,
            0.406,
            0.40612485,
            0.40649941,
            0.40712366,
            0.40799762,
            0.40912128,
            0.41049465,
            0.41211772,
            0.41399049,
            0.41611296,
            0.41848514,
            0.42110702,
            0.4239786,
            0.42709988,
            0.43047087,
            0.43409156,
            0.43796195,
            0.44208205,
            0.44645184,
            0.45107134,
            0.45594055,
            0.46105945,
            0.46642806,
            0.47204637,
            0.47791439,
            0.4840321,
            0.49039952,
            0.49701665,
            0.50388347,
            0.511,
            0.511,
            0.511,
            0.511,
            0.511,
            0.511,
            0.511,
            0.511,
            0.511,
            0.511,
            0.511,
            0.511,
            0.50388347,
            0.49701665,
            0.49039952,
            0.4840321,
            0.47791439,
            0.47204637,
            0.46642806,
            0.46105945,
            0.45594055,
            0.45107134,
            0.44645184,
            0.44208205,
            0.43796195,
            0.43409156,
            0.43047087,
            0.42709988,
            0.4239786,
            0.42110702,
            0.41848514,
            0.41611296,
            0.41399049,
            0.41211772,
            0.41049465,
            0.40912128,
            0.40799762,
            0.40712366,
            0.40649941,
            0.40612485,
            0.406,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]

        np.testing.assert_array_almost_equal(amsterdam_wf, expected_wf)
