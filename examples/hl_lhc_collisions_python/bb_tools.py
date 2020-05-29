import copy

import pandas as pd

import numpy as np
from scipy.special import erf, erfinv

from madpoint import MadPoint

_sigma_names = [11, 12, 13, 14, 22, 23, 24, 33, 34, 44]
_beta_names = ["betx", "bety"]

def norm(v):
    return np.sqrt(np.sum(v ** 2))

def get_points_twissdata_for_element_type(
    mad, seq_name, ele_type=None, slot_id=None, use_survey=True, use_twiss=True
):

    elements, element_names = get_elements(
        seq=mad.sequence[seq_name], ele_type=ele_type, slot_id=slot_id
    )

    points, twissdata = get_points_twissdata_for_elements(
        element_names,
        mad,
        seq_name,
        use_survey=use_survey,
        use_twiss=use_twiss,
    )

    return elements, element_names, points, twissdata

def get_elements(seq, ele_type=None, slot_id=None):

    elements = []
    element_names = []
    for ee in seq.elements:

        if ele_type is not None:
            if ee.base_type.name != ele_type:
                continue

        if slot_id is not None:
            if ee.slot_id != slot_id:
                continue

        elements.append(ee)
        element_names.append(ee.name)

    return elements, element_names


def get_points_twissdata_for_elements(
    ele_names, mad, seq_name, use_survey=True, use_twiss=True
):

    mad.use(sequence=seq_name)

    mad.twiss()

    if use_survey:
        mad.survey()

    bb_xyz_points = []
    bb_twissdata = {
        kk: []
        for kk in _sigma_names
        + _beta_names
        + "dispersion_x dispersion_y x y".split()
    }
    for eename in ele_names:
        bb_xyz_points.append(
            MadPoint(
                eename + ":1", mad, use_twiss=use_twiss, use_survey=use_survey
            )
        )

        i_twiss = np.where(mad.table.twiss.name == (eename + ":1"))[0][0]

        for sn in _sigma_names:
            bb_twissdata[sn].append(
                getattr(mad.table.twiss, "sig%d" % sn)[i_twiss]
            )

        for kk in ["betx", "bety"]:
            bb_twissdata[kk].append(mad.table.twiss[kk][i_twiss])
        gamma = mad.table.twiss.summary.gamma
        beta = np.sqrt(1.0 - 1.0 / (gamma * gamma))
        for pp in ["x", "y"]:
            bb_twissdata["dispersion_" + pp].append(
                mad.table.twiss["d" + pp][i_twiss] * beta
            )
            bb_twissdata[pp].append(mad.table.twiss[pp][i_twiss])
        # , 'dx', 'dy']:

    return bb_xyz_points, bb_twissdata


def get_bb_names_madpoints_sigmas(
    mad, seq_name, use_survey=True, use_twiss=True
):
    (
        _,
        element_names,
        points,
        twissdata,
    ) = get_points_twissdata_for_element_type(
        mad,
        seq_name,
        ele_type="beambeam",
        slot_id=None,
        use_survey=use_survey,
        use_twiss=use_twiss,
    )
    sigmas = {kk: twissdata[kk] for kk in _sigma_names}
    return element_names, points, sigmas

# %% From https://github.com/giadarol/WeakStrong/blob/master/slicing.py
def constant_charge_slicing_gaussian(N_part_tot, sigmaz, N_slices):
    if N_slices>1:
        # working with intensity 1. and rescling at the end
        Qi = (np.arange(N_slices)/float(N_slices))[1:]
        
        z_cuts = np.sqrt(2)*sigmaz*erfinv(2*Qi-1.)
        
        #~ import pdb; pdb.set_trace()
        
        z_centroids = []
        first_centroid = -sigmaz/np.sqrt(2*np.pi)*np.exp(-z_cuts[0]**2/(2*sigmaz*sigmaz))*float(N_slices)
        z_centroids.append(first_centroid)
        for ii in range(N_slices-2):
            this_centroid = -sigmaz/np.sqrt(2*np.pi)*(np.exp(-z_cuts[ii+1]**2/(2*sigmaz*sigmaz))-
                                                      np.exp(-z_cuts[ii]**2/(2*sigmaz*sigmaz)))*float(N_slices) 
            #the multiplication times n slices comes from the fact that we have to divide by the slice charge, i.e. 1./N
            z_centroids.append(this_centroid)                                         

        last_centroid = sigmaz/np.sqrt(2*np.pi)*np.exp(-z_cuts[-1]**2/(2*sigmaz*sigmaz))*float(N_slices)
        z_centroids.append(last_centroid)
        
        z_centroids = np.array(z_centroids)
        
        N_part_per_slice = z_centroids*0.+N_part_tot/float(N_slices)
    elif N_slices==1:
        z_centroids = np.array([0.])
        z_cuts = []
        N_part_per_slice = np.array([N_part_tot])
        
    else:
        raise ValueError('Invalid number of slices')
    
    return z_centroids, z_cuts, N_part_per_slice


# %% define elementDefinition function
import numpy as np

def elementName(label, IRNumber, beam, identifier):
    if identifier >0:
        sideTag='.r'
    elif identifier < 0:
        sideTag='.l'
    else:
        sideTag='.c'
    return f'{label}{sideTag}{IRNumber}{beam}_{np.abs(identifier):02}'

def elementDefinition(elementName, elementClass, elementAttributes):
    return f'{elementName} : {elementClass}, {elementAttributes};'

# %% define elementInstallation function
def elementInstallation(element_name, element_class, atPosition, fromLocation=None):
    if fromLocation==None:
        return f'install, element={element_name}, class={element_class}, at={atPosition};'
    else:
        return f'install, element={element_name}, class={element_class}, at={atPosition}, from={fromLocation};'


def generate_set_of_bb_encounters_1beam(
    circumference=26658.8832,
    harmonic_number = 35640,
    bunch_spacing_buckets = 10,
    numberOfHOSlices = 11,
    bunch_charge_ppb = 0.,
    sigt=0.0755,
    relativistic_beta=1.,
    ip_names = ['ip1', 'ip2', 'ip5', 'ip8'],
    numberOfLRPerIRSide=[21, 20, 21, 20],
    beam_name = 'b1',
    other_beam_name = 'b2'
    ):


    # Long-Range
    myBBLRlist=[]
    for ii, ip_nn in enumerate(ip_names):
        for identifier in (list(range(-numberOfLRPerIRSide[ii],0))+list(range(1,numberOfLRPerIRSide[ii]+1))):
            myBBLRlist.append({'label':'bb_lr', 'ip_name':ip_nn, 'beam':beam_name, 'other_beam':other_beam_name,
                'identifier':identifier})

    if len(myBBLRlist)>0:
        myBBLR=pd.DataFrame(myBBLRlist)[['beam','other_beam','ip_name','label','identifier']]

        myBBLR['self_charge_ppb'] = bunch_charge_ppb
        myBBLR['self_relativistic_beta'] = relativistic_beta
        myBBLR['elementName']=myBBLR.apply(lambda x: elementName(x.label, x.ip_name.replace('ip', ''), x.beam, x.identifier), axis=1)
        myBBLR['other_elementName']=myBBLR.apply(
                lambda x: elementName(x.label, x.ip_name.replace('ip', ''), x.other_beam, x.identifier), axis=1)
        # where circ is used
        BBSpacing = circumference / harmonic_number * bunch_spacing_buckets / 2.
        myBBLR['atPosition']=BBSpacing*myBBLR['identifier']
        # assuming a sequence rotated in IR3
    else:
        myBBLR = pd.DataFrame()

    # Head-On
    numberOfSliceOnSide=int((numberOfHOSlices-1)/2)
    # to check: sigz of the luminous region
    # where sigt is used
    sigzLumi=sigt/2
    z_centroids, z_cuts, N_part_per_slice = constant_charge_slicing_gaussian(1,sigzLumi,numberOfHOSlices)
    myBBHOlist=[]

    for ip_nn in ip_names:
        for identifier in (list(range(-numberOfSliceOnSide,0))+[0]+list(range(1,numberOfSliceOnSide+1))):
            myBBHOlist.append({'label':'bb_ho', 'ip_name':ip_nn, 'other_beam':other_beam_name, 'beam':beam_name, 'identifier':identifier})

    myBBHO=pd.DataFrame(myBBHOlist)[['beam','other_beam', 'ip_name','label','identifier']]


    myBBHO['self_charge_ppb'] = bunch_charge_ppb/numberOfHOSlices
    myBBHO['self_relativistic_beta'] = relativistic_beta
    for ip_nn in ip_names:
        myBBHO.loc[myBBHO['ip_name']==ip_nn, 'atPosition']=list(z_centroids)

    myBBHO['elementName']=myBBHO.apply(lambda x: elementName(x.label, x.ip_name.replace('ip', ''), x.beam, x.identifier), axis=1)
    myBBHO['other_elementName']=myBBHO.apply(lambda x: elementName(x.label, x.ip_name.replace('ip', ''), x.other_beam, x.identifier), axis=1)
    # assuming a sequence rotated in IR3

    myBB=pd.concat([myBBHO, myBBLR],sort=False)
    myBB = myBB.set_index('elementName', drop=False, verify_integrity=True).sort_index()

    return myBB

def generate_mad_bb_info(bb_df, mode='dummy', madx_reference_bunch_charge=1):

    if mode == 'dummy':
        bb_df['elementClass']='beambeam'
        eattributes = lambda charge, label:'sigx = 0.1, '   + \
                    'sigy = 0.1, '   + \
                    'xma  = 1, '     + \
                    'yma  = 1, '     + \
                    f'charge = 0*{charge}, ' +\
                    'slot_id = %d'%({'bb_lr': 4, 'bb_ho': 6}[label]) # need to add 60 for central
        bb_df['elementDefinition']=bb_df.apply(lambda x: elementDefinition(x.elementName, x.elementClass, eattributes(x['self_charge_ppb'], x['label'])), axis=1)
        bb_df['elementInstallation']=bb_df.apply(lambda x: elementInstallation(x.elementName, x.elementClass, x.atPosition, x.ip_name), axis=1)
    elif mode=='from_dataframe':
        bb_df['elementClass']='beambeam'
        eattributes = lambda sigx, sigy, xma, yma, charge, label:f'sigx = {sigx}, '   + \
                    f'sigy = {sigy}, '   + \
                    f'xma  = {xma}, '     + \
                    f'yma  = {yma}, '     + \
                    f'charge := on_bb_switch*{charge}, ' +\
                    'slot_id = %d'%({'bb_lr': 4, 'bb_ho': 6}[label]) # need to add 60 for central
        bb_df['elementDefinition']=bb_df.apply(lambda x: elementDefinition(x.elementName, x.elementClass,
            eattributes(np.sqrt(x['other_Sigma_11']),np.sqrt(x['other_Sigma_33']),
                x['separation_x'], x['separation_y'],
                x['other_charge_ppb']/madx_reference_bunch_charge, x['label'])),
            axis=1)
        bb_df['elementInstallation']=bb_df.apply(lambda x: elementInstallation(x.elementName, x.elementClass, x.atPosition, x.ip_name), axis=1)
    else:
        raise ValueError("mode must be 'dummy' or 'from_dataframe")

    return bb_df
def get_counter_rotating(bb_df):

    c_bb_df = pd.DataFrame(index=bb_df.index)

    c_bb_df['beam'] = bb_df['beam']
    c_bb_df['other_beam'] = bb_df['other_beam']
    c_bb_df['ip_name'] = bb_df['ip_name']
    c_bb_df['label'] = bb_df['label']
    c_bb_df['identifier'] = bb_df['identifier']
    c_bb_df['elementClass'] = bb_df['elementClass']
    c_bb_df['elementName'] = bb_df['elementName']
    c_bb_df['self_charge_ppb'] = bb_df['self_charge_ppb']
    c_bb_df['other_charge_ppb'] = bb_df['other_charge_ppb']
    c_bb_df['other_elementName'] = bb_df['other_elementName']

    c_bb_df['atPosition'] = bb_df['atPosition'] * (-1.)

    c_bb_df['elementDefinition'] = np.nan
    c_bb_df['elementInstallation'] = np.nan

    c_bb_df['self_lab_position'] = np.nan
    c_bb_df['other_lab_position'] = np.nan

    c_bb_df['self_Sigma_11'] = bb_df['self_Sigma_11'] * (-1.) * (-1.)                  # x * x
    c_bb_df['self_Sigma_12'] = bb_df['self_Sigma_12'] * (-1.) * (-1.) * (-1.)          # x * dx / ds
    c_bb_df['self_Sigma_13'] = bb_df['self_Sigma_13'] * (-1.)                          # x * y
    c_bb_df['self_Sigma_14'] = bb_df['self_Sigma_14'] * (-1.) * (-1.)                  # x * dy / ds
    c_bb_df['self_Sigma_22'] = bb_df['self_Sigma_22'] * (-1.) * (-1.) * (-1.) * (-1.)  # dx / ds * dx / ds
    c_bb_df['self_Sigma_23'] = bb_df['self_Sigma_23'] * (-1.) * (-1.)                  # dx / ds * y
    c_bb_df['self_Sigma_24'] = bb_df['self_Sigma_24'] * (-1.) * (-1.) * (-1.)          # dx / ds * dy / ds
    c_bb_df['self_Sigma_33'] = bb_df['self_Sigma_33']                                  # y * y
    c_bb_df['self_Sigma_34'] = bb_df['self_Sigma_34'] * (-1.)                          # y * dy / ds
    c_bb_df['self_Sigma_44'] = bb_df['self_Sigma_44'] * (-1.) * (-1.)                  # dy / ds * dy / ds

    c_bb_df['other_Sigma_11'] = bb_df['other_Sigma_11'] * (-1.) * (-1.)
    c_bb_df['other_Sigma_12'] = bb_df['other_Sigma_12'] * (-1.) * (-1.) * (-1.)
    c_bb_df['other_Sigma_13'] = bb_df['other_Sigma_13'] * (-1.)
    c_bb_df['other_Sigma_14'] = bb_df['other_Sigma_14'] * (-1.) * (-1.)
    c_bb_df['other_Sigma_22'] = bb_df['other_Sigma_22'] * (-1.) * (-1.) * (-1.) * (-1.)
    c_bb_df['other_Sigma_23'] = bb_df['other_Sigma_23'] * (-1.) * (-1.)
    c_bb_df['other_Sigma_24'] = bb_df['other_Sigma_24'] * (-1.) * (-1.) * (-1.)
    c_bb_df['other_Sigma_33'] = bb_df['other_Sigma_33']
    c_bb_df['other_Sigma_34'] = bb_df['other_Sigma_34'] * (-1.)
    c_bb_df['other_Sigma_44'] = bb_df['other_Sigma_44'] * (-1.) * (-1.)

    c_bb_df['other_relativistic_beta']=bb_df['other_relativistic_beta']
    c_bb_df['separation_x'] = bb_df['separation_x'] * (-1.)
    c_bb_df['separation_y'] = bb_df['separation_y']

    c_bb_df['dpx'] = bb_df['dpx'] * (-1.) * (-1.)
    c_bb_df['dpy'] = bb_df['dpy'] * (-1.)

    # Compute phi and alpha from dpx and dpy
    compute_local_crossing_angle_and_plane(c_bb_df)

    return c_bb_df

def install_lenses_in_sequences(mad, bb_data_frames,
    beam_names, sequence_names):

    for bb_df in bb_data_frames:
        mad.input(bb_df['elementDefinition'].str.cat(sep='\n'))

    # %% seqedit
    for beam, bb_df, seq in zip(beam_names, bb_data_frames, sequence_names):
        myBBDFFiltered=bb_df[bb_df['beam']==beam]
        mad.input(f'seqedit, sequence={"lhc"+beam};')
        mad.input('flatten;')
        mad.input(myBBDFFiltered['elementInstallation'].str.cat(sep='\n'))
        mad.input('flatten;')
        mad.input(f'endedit;')

def get_geometry_and_optics_b1_b2(mad, bb_df_b1, bb_df_b2):

    for beam, bbdf in zip(['b1', 'b2'], [bb_df_b1, bb_df_b2]):
        # Get positions of the bb encounters (absolute from survey), closed orbit
        # and orientation of the local reference system (MadPoint objects)
        names, positions, sigmas = get_bb_names_madpoints_sigmas(
            mad, seq_name="lhc"+beam
        )

        temp_df = pd.DataFrame()
        temp_df['self_lab_position'] = positions
        temp_df['elementName'] = names
        for ss in sigmas.keys():
            temp_df[f'self_Sigma_{ss}'] = sigmas[ss]

        temp_df = temp_df.set_index('elementName', verify_integrity=True).sort_index()

        for cc in temp_df.columns:
            bbdf[cc] = temp_df[cc]

def get_survey_ip_position_b1_b2(mad,
        ip_names = ['ip1', 'ip2', 'ip5', 'ip8']):

    # Get ip position in the two surveys

    ip_position_df = pd.DataFrame()

    for beam in ['b1', 'b2']:
        mad.use("lhc"+beam)
        mad.survey()
        for ipnn in ip_names:
            ip_position_df.loc[ipnn, beam] = MadPoint.from_survey((ipnn + ":1").lower(), mad)

    return ip_position_df

def get_partner_corrected_position_and_optics(bb_df_b1, bb_df_b2, ip_position_df):

    dict_dfs = {'b1': bb_df_b1, 'b2': bb_df_b2}

    for self_beam_nn in ['b1', 'b2']:

        self_df = dict_dfs[self_beam_nn]

        for ee in self_df.index:
            other_beam_nn = self_df.loc[ee, 'other_beam']
            other_df = dict_dfs[other_beam_nn]
            other_ee = self_df.loc[ee, 'other_elementName']

            # Get position of the other beam in its own survey
            other_lab_position = copy.deepcopy(other_df.loc[other_ee, 'self_lab_position'])

            # Compute survey shift based on closest ip
            closest_ip = self_df.loc[ee, 'ip_name']
            survey_shift = (
                    ip_position_df.loc[closest_ip, other_beam_nn].p
                  - ip_position_df.loc[closest_ip, self_beam_nn].p)

            # Shift to reference system of self
            other_lab_position.shift_survey(survey_shift)

            # Store positions
            self_df.loc[ee, 'other_lab_position'] = other_lab_position

            # Get sigmas of the other beam in its own survey
            for ss in _sigma_names:
                self_df.loc[ee, f'other_Sigma_{ss}'] = other_df.loc[other_ee, f'self_Sigma_{ss}']
            # Get charge of other beam
            self_df.loc[ee, 'other_charge_ppb'] = other_df.loc[other_ee, 'self_charge_ppb']
            self_df.loc[ee, 'other_relativistic_beta'] = other_df.loc[other_ee, 'self_relativistic_beta']

def compute_separations(bb_df):

    sep_x, sep_y = find_bb_separations(
        points_weak=bb_df['self_lab_position'].values,
        points_strong=bb_df['other_lab_position'].values,
        names=bb_df.index.values,
        )

    bb_df['separation_x'] = sep_x
    bb_df['separation_y'] = sep_y

def compute_dpx_dpy(bb_df):
    # Defined as (weak) - (strong)
    for ee in bb_df.index:
        dpx = (bb_df.loc[ee, 'self_lab_position'].tpx
                - bb_df.loc[ee, 'other_lab_position'].tpx)
        dpy = (bb_df.loc[ee, 'self_lab_position'].tpy
                - bb_df.loc[ee, 'other_lab_position'].tpy)

        bb_df.loc[ee, 'dpx'] = dpx
        bb_df.loc[ee, 'dpy'] = dpy

def compute_local_crossing_angle_and_plane(bb_df):

    for ee in bb_df.index:
        alpha, phi = find_alpha_and_phi(
                bb_df.loc[ee, 'dpx'], bb_df.loc[ee, 'dpy'])

        bb_df.loc[ee, 'alpha'] = alpha
        bb_df.loc[ee, 'phi'] = phi

def find_alpha_and_phi(dpx, dpy):

    absphi = np.sqrt(dpx ** 2 + dpy ** 2) / 2.0

    if absphi < 1e-20:
        phi = absphi
        alpha = 0.0
    else:
        if dpy>=0.:
            if dpx>=0:
                # First quadrant
                if np.abs(dpx) >= np.abs(dpy):
                    # First octant
                    phi = absphi
                    alpha = np.arctan(dpy/dpx)
                else:
                    # Second octant
                    phi = absphi
                    alpha = 0.5*np.pi - np.arctan(dpx/dpy)
            else: #dpx<0
                # Second quadrant
                if np.abs(dpx) <  np.abs(dpy):
                    # Third octant
                    phi = absphi
                    alpha = 0.5*np.pi - np.arctan(dpx/dpy)
                else:
                    # Forth  octant
                    phi = -absphi
                    alpha = np.arctan(dpy/dpx)
        else: #dpy<0
            if dpx<=0:
                # Third quadrant
                if np.abs(dpx) >= np.abs(dpy):
                    # Fifth octant
                    phi = -absphi
                    alpha = np.arctan(dpy/dpx)
                else:
                    # Sixth octant
                    phi = -absphi
                    alpha = 0.5*np.pi - np.arctan(dpx/dpy)
            else: #dpx>0
                # Forth quadrant
                if np.abs(dpx) <= np.abs(dpy):
                    # Seventh octant
                    phi = -absphi
                    alpha = 0.5*np.pi - np.arctan(dpx/dpy)
                else:
                    # Eighth octant
                    phi = absphi
                    alpha = np.arctan(dpy/dpx)

    return alpha, phi



def get_bb_names_madpoints_sigmas(
    mad, seq_name, use_survey=True, use_twiss=True
):
    (
        _,
        element_names,
        points,
        twissdata,
    ) = get_points_twissdata_for_element_type(
        mad,
        seq_name,
        ele_type="beambeam",
        slot_id=None,
        use_survey=use_survey,
        use_twiss=use_twiss,
    )
    sigmas = {kk: twissdata[kk] for kk in _sigma_names}
    return element_names, points, sigmas


def compute_shift_strong_beam_based_on_close_ip(
    points_weak, points_strong, IPs_survey_weak, IPs_survey_strong
):
    strong_shift = []
    for i_bb, _ in enumerate(points_weak):

        pbw = points_weak[i_bb]
        pbs = points_strong[i_bb]

        # Find closest IP
        d_ip = 1e6
        use_ip = 0
        for ip in IPs_survey_weak.keys():
            dd = norm(pbw.p - IPs_survey_weak[ip].p)
            if dd < d_ip:
                use_ip = ip
                d_ip = dd

        # Shift Bs
        shift_ws = IPs_survey_strong[use_ip].p - IPs_survey_weak[use_ip].p
        strong_shift.append(shift_ws)
    return strong_shift


def find_bb_separations(points_weak, points_strong, names=None):

    if names is None:
        names = ["bb_%d" % ii for ii in range(len(points_weak))]

    sep_x = []
    sep_y = []
    for i_bb, name_bb in enumerate(names):

        pbw = points_weak[i_bb]
        pbs = points_strong[i_bb]

        # Find vws
        vbb_ws = points_strong[i_bb].p - points_weak[i_bb].p

        # Check that the two reference system are parallel
        try:
            assert norm(pbw.ex - pbs.ex) < 1e-10  # 1e-4 is a reasonable limit
            assert norm(pbw.ey - pbs.ey) < 1e-10  # 1e-4 is a reasonable limit
            assert norm(pbw.ez - pbs.ez) < 1e-10  # 1e-4 is a reasonable limit
        except AssertionError:
            print(name_bb, "Reference systems are not parallel")
            if (
                np.sqrt(
                    norm(pbw.ex - pbs.ex) ** 2
                    + norm(pbw.ey - pbs.ey) ** 2
                    + norm(pbw.ez - pbs.ez) ** 2
                )
                < 5e-3
            ):
                print("Smaller that 5e-3, tolerated.")
            else:
                raise ValueError("Too large! Stopping.")

        # Check that there is no longitudinal separation
        try:
            assert np.abs(np.dot(vbb_ws, pbw.ez)) < 1e-4
        except AssertionError:
            print(name_bb, "The beams are longitudinally shifted")

        # Find separations
        sep_x.append(np.dot(vbb_ws, pbw.ex))
        sep_y.append(np.dot(vbb_ws, pbw.ey))

    return sep_x, sep_y

