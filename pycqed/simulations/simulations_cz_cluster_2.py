import time
# import numpy as np
# import qutip as qtp
from pycqed.measurement import detector_functions as det
from scipy.interpolate import interp1d
from pycqed.measurement.waveform_control_CC import waveforms_flux as wfl
import scipy
# import matplotlib.pyplot as plt
import logging
#np.set_printoptions(threshold=np.inf)
import copy




# operators
b = qtp.tensor(qtp.destroy(3), qtp.qeye(3))  # LSB is static qubit
a = qtp.tensor(qtp.qeye(3), qtp.destroy(3))
n_q0 = a.dag() * a
n_q1 = b.dag() * b

H_coupling = (a.dag() + a) * (b + b.dag())
H_c = n_q0


scalefactor=1  # scalefactor not used anymore





# Hamiltonian
def coupled_transmons_hamiltonian(w_q0, w_q1, alpha_q0, alpha_q1, J, w_bus):
    """
    Hamiltonian of two coupled anharmonic transmons.
    Because the intention is to tune one qubit into resonance with the other,
    the number of levels is limited.
        q1 -> static qubit, 3-levels
        q0 -> fluxing qubit, 3-levels

    intended avoided crossing:
        11 <-> 02     (q1 is the first (left) qubit and q0 the second (right) one)

    N.B. the frequency of q0 is expected to be larger than that of q1
        w_q0 > w_q1
        and the anharmonicities alpha negative
    """

    raise NotImplementedError("Old way of handling the hamiltonian H_0. Use calc_hamiltonian")

    eps=0
    delta_q1=w_q1-w_bus
    delta_q0_interactionpoint=(w_q1-alpha_q0)-w_bus
    delta_q0=(w_q0+eps)-w_bus

    J_new = J / ((delta_q1+delta_q0_interactionpoint)/(delta_q1*delta_q0_interactionpoint)) * (delta_q1+delta_q0)/(delta_q1*delta_q0)

    H_0 = w_q0 * n_q0 + w_q1 * n_q1 +  \
        1/2*alpha_q0*(a.dag()*a.dag()*a*a) + 1/2*alpha_q1*(b.dag()*b.dag()*b*b) +\
        J_new * (a.dag() + a) * (b + b.dag())
    return H_0


def hamiltonian_timedependent(H_0,eps,w_bus):

    raise NotImplementedError("Old way of handling the hamiltonian time-dependent. Use calc_hamiltonian")

    w_q0=np.real(H_0[1,1])
    w_q1=np.real(H_0[3,3])
    alpha_q0=np.real(H_0[2,2])-2*w_q0
    J=np.real(H_0[1,3])

    delta_q1=w_q1-w_bus
    delta_q0_sweetspot=(w_q0)-w_bus
    delta_q0=(w_q0+eps)-w_bus

    J_new = J / ((delta_q1+delta_q0_sweetspot)/(delta_q1*delta_q0_sweetspot)) * (delta_q1+delta_q0)/(delta_q1*delta_q0)

    return H_0+eps*H_c+(J_new-J)*H_coupling



# target in the case with no noise
# note that the Hilbert space is H_q1 /otimes H_q0
# so the ordering of basis states below is 00,01,02,10,11,12,20,21,22
U_target = qtp.Qobj([[1, 0, 0, 0, 0, 0, 0, 0, 0],
                     [0, 1, 0, 0, 0, 0, 0, 0, 0],
                     [0, 0, -1, 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, 1, 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, -1, 0, 0, 0, 0],
                     [0, 0, 0, 0, 0, 1, 0, 0, 0],
                     [0, 0, 0, 0, 0, 0, 1, 0, 0],
                     [0, 0, 0, 0, 0, 0, 0, 1, 0],
                     [0, 0, 0, 0, 0, 0, 0, 0, 1]],
                    type='oper',
                    dims=[[3, 3], [3, 3]])
#U_target._type = 'oper'
U_target_diffdims = qtp.Qobj([[1, 0, 0, 0, 0, 0, 0, 0, 0],
                     [0, 1, 0, 0, 0, 0, 0, 0, 0],
                     [0, 0, -1, 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, 1, 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, -1, 0, 0, 0, 0],
                     [0, 0, 0, 0, 0, 1, 0, 0, 0],
                     [0, 0, 0, 0, 0, 0, 1, 0, 0],
                     [0, 0, 0, 0, 0, 0, 0, 1, 0],
                     [0, 0, 0, 0, 0, 0, 0, 0, 1]],
                    type='oper',
                    dims=[[9], [9]])     # otherwise average_gate_fidelity doesn't work

# if there is noise the target is the corresponding superoperator
U_super_target = qtp.to_super(U_target)

'''
remember that qutip uses the Liouville (matrix) representation for superoperators,
with column stacking.
This means that 
rho_{xy,x'y'}=rho[3*x+y,3*x'+y']
rho_{xy,x'y'}=operator_to_vector(rho)[3*x+y+27*x'+9*y']
where xy is the row and x'y' is the column
'''


def plot(x_plot_vec,y_plot_vec,title='No title',xlabel='No xlabel',ylabel='No ylabel',legend_labels=list(),yscale='linear'):
    # tool for plotting
    # x_plot_vec and y_plot_vec should be passed as either lists or np.array

    if isinstance(y_plot_vec,list):
        y_length=len(y_plot_vec)
    else:
        y_length=np.size(y_plot_vec)

    if legend_labels==[]:
        legend_labels=np.arange(y_length)

    for i in range(y_length):

        if isinstance(y_plot_vec[i],list):
            y_plot_vec[i]=np.array(y_plot_vec[i])
        if isinstance(legend_labels[i],int):
            legend_labels[i]=str(legend_labels[i])

        if len(x_plot_vec)==1:
            if isinstance(x_plot_vec[0],list):
                x_plot_vec[0]=np.array(x_plot_vec[0])
            plt.plot(x_plot_vec[0], y_plot_vec[i], label=legend_labels[i])
        else:
            if isinstance(x_plot_vec[i],list):
                x_plot_vec[i]=np.array(x_plot_vec[i])
            plt.plot(x_plot_vec[i], y_plot_vec[i], label=legend_labels[i])

    plt.legend()
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.yscale(yscale)
    plt.show()



def jump_operators(T1_q0,T1_q1):

    c_ops=[]
    if T1_q0 != 0:
        c_ops.append(np.sqrt(1/T1_q0)*a)
    if T1_q1 != 0:
        c_ops.append(np.sqrt(1/T1_q1)*b)
    return c_ops



def c_ops_amplitudedependent(T1_q0,T1_q1,Tphi01_q0_vec,Tphi01_q1):
    # case where the pure decoherence for qubit q0 is time dependent, or better pulse-amplitude dependent

    c_ops=[]

    if T1_q0 != 0:
        c_ops.append(np.sqrt(1/T1_q0)*a)

    if T1_q1 != 0:
        c_ops.append(np.sqrt(1/T1_q1)*b)

    if Tphi01_q1 != 0:                                 # we automatically put also the decoherence for 12 and 02
        sigmaZinqutrit = qtp.Qobj([[1,0,0],
                                    [0,-1,0],
                                    [0,0,0]])
        collapse=qtp.tensor(sigmaZinqutrit,qtp.qeye(3))
        c_ops.append(collapse*np.sqrt(1/(2*Tphi01_q1)))

        Tphi12_q1=Tphi01_q1
        sigmaZinqutrit = qtp.Qobj([[0,0,0],
                                    [0,1,0],
                                    [0,0,-1]])
        collapse=qtp.tensor(sigmaZinqutrit,qtp.qeye(3))
        c_ops.append(collapse*np.sqrt(1/(2*Tphi12_q1)))

        Tphi02_q1=Tphi01_q1/2
        sigmaZinqutrit = qtp.Qobj([[1,0,0],
                                    [0,0,0],
                                    [0,0,-1]])
        collapse=qtp.tensor(sigmaZinqutrit,qtp.qeye(3))
        c_ops.append(collapse*np.sqrt(1/(2*Tphi02_q1)))

    if Tphi01_q0_vec != []:                                 # we automatically put also the decoherence for 12 and 02
        sigmaZinqutrit = qtp.Qobj([[1,0,0],
                                    [0,-1,0],
                                    [0,0,0]])
        collapse=qtp.tensor(qtp.qeye(3),sigmaZinqutrit)
        c_ops.append([collapse,np.sqrt(1/(2*Tphi01_q0_vec))])

        Tphi12_q0_vec=Tphi01_q0_vec
        sigmaZinqutrit = qtp.Qobj([[0,0,0],
                                    [0,1,0],
                                    [0,0,-1]])
        collapse=qtp.tensor(qtp.qeye(3),sigmaZinqutrit)
        c_ops.append([collapse,np.sqrt(1/(2*Tphi12_q0_vec))])

        Tphi02_q0_vec=Tphi01_q0_vec/2
        sigmaZinqutrit = qtp.Qobj([[1,0,0],
                                    [0,0,0],
                                    [0,0,-1]])
        collapse=qtp.tensor(qtp.qeye(3),sigmaZinqutrit)
        c_ops.append([collapse,np.sqrt(1/(2*Tphi02_q0_vec))])

    return c_ops




def rotating_frame_transformation_propagator(U, t: float,
                                  w_q0: float=0, w_q1: float =0):
    """
    Transforms the frame of the unitary according to
        U' = U_{RF}*U
        NOTE: remember that this is how the time evolution operator changes from one picture to another
    with
        U_{RF} = e^{-i w_q0 a^dag a t } otimes e^{-i w_q1 b^dag b t }
        (method for the case where we are simply rotating away the two qubit frequencies)

    Args:
        U (QObj): Unitary to be transformed
        t (float): time at which to transform
        w_q0 (float): freq of frame for q0
        w_q1 (float): freq of frame for q1

    """
    logging.warning('Recommended to use rotating_frame_transformation_new passing the hamiltonian as an argument.')


    U_RF = (1j*w_q0*n_q0*t).expm() * (1j*w_q1*n_q1*t).expm()
    if U.type=='super':
        U_RF=qtp.to_super(U_RF)

    U_prime = U_RF * U  
    """ U_RF only on one side because that's the operator that
    satisfies the Schroedinger equation in the interaction picture.
    """

    return U_prime


def rotating_frame_transformation_propagator_new(U, t: float, H):
    """
    Transforms the frame of the unitary according to
        U' = U_{RF}*U
        NOTE: remember that this is how the time evolution operator changes from one picture to another

    Args:
        U (QObj): Unitary to be transformed
        t (float): time at which to transform
        H (QObj): hamiltonian to be rotated away

    """

    U_RF = (1j*H*t).expm()
    if U.type=='super':
        U_RF=qtp.to_super(U_RF)

    U_prime = U_RF * U  
    """ U_RF only on one side because that's the operator that
    satisfies the Schroedinger equation in the interaction picture.
    """

    return U_prime


def rotating_frame_transformation_operators(operator, t: float, H):
    """
    Transforms the frame of an operator (hamiltonian, or jump operator) according to
        O' = U_{RF}*O*U_{RF}^dag

    Args:
        operator (QObj): operator to be transformed
        t (float): time at which to transform
        H (QObj): hamiltonian to be rotated away

    """

    U_RF = (1j*H*t).expm()

    return U_RF * H * U_RF.dag()


def correct_reference(U,w_q1,w_q0,t):
    # w_qi should be a frequency (not including the 2*pi factor). Moreover they and t should be in the same scale.
    # this functions should be used just to make sanity checks.
    phase_to_correct_q1 = w_q1*(2*np.pi)*t
    phase_to_correct_q0 = w_q0*(2*np.pi)*t

    Ucorrection = qtp.Qobj([[1, 0, 0, 0, 0, 0, 0, 0, 0],
                     [0, np.exp(1j*phase_to_correct_q0), 0, 0, 0, 0, 0, 0, 0],
                     [0, 0, 1, 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, np.exp(1j*phase_to_correct_q1), 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, np.exp(1j*(phase_to_correct_q0+phase_to_correct_q1)), 0, 0, 0, 0],
                     [0, 0, 0, 0, 0, np.exp(1j*phase_to_correct_q1), 0, 0, 0],
                     [0, 0, 0, 0, 0, 0, 1, 0, 0],
                     [0, 0, 0, 0, 0, 0, 0, np.exp(1j*phase_to_correct_q0), 0],
                     [0, 0, 0, 0, 0, 0, 0, 0, 1]],
                    type='oper',
                    dims=[[3, 3], [3, 3]])

    if U.type=='oper':
        return Ucorrection*U
    elif U.type=='super':
        return qtp.to_super(Ucorrection)*U


def phases_from_superoperator(U):
    """
    Returns the phases from the unitary or superoperator U
    """
    if U.type=='oper':
        phi_00 = np.rad2deg(np.angle(U[0, 0]))  # expected to equal 0 because of our
        # choice for the energy, not because of rotating frame. But not guaranteed including the coupling
        phi_01 = np.rad2deg(np.angle(U[1, 1]))
        phi_10 = np.rad2deg(np.angle(U[3, 3]))
        phi_11 = np.rad2deg(np.angle(U[4, 4]))
        phi_02 = np.rad2deg(np.angle(U[2, 2]))  # used only for avgatefid_superoperator_phasecorrected
        phi_20 = np.rad2deg(np.angle(U[6, 6]))  # used only for avgatefid_superoperator_phasecorrected

    elif U.type=='super':
        phi_00 = 0   # we set it to 0 arbitrarily but it is indeed not knowable
        phi_01 = np.rad2deg(np.angle(U[1, 1]))   # actually phi_01-phi_00 etc
        phi_10 = np.rad2deg(np.angle(U[3, 3]))
        phi_11 = np.rad2deg(np.angle(U[4, 4]))
        phi_02 = np.rad2deg(np.angle(U[2, 2]))
        phi_20 = np.rad2deg(np.angle(U[6, 6]))

    phi_cond = (phi_11 - phi_01 - phi_10 + phi_00) % 360  # still the right formula independently from phi_00

    return phi_00, phi_01, phi_10, phi_11, phi_02, phi_20, phi_cond



def pro_avfid_superoperator_compsubspace(U,L1):
    """
    Average process (gate) fidelity in the qubit computational subspace for two qutrits.
    Leakage has to be taken into account, see Woods & Gambetta.
    The function assumes that the computational subspace (:= the 4 energy levels chosen as the two qubits) is given by 
            the standard basis |0> /otimes |0>, |0> /otimes |1>, |1> /otimes |0>, |1> /otimes |1>.
            If this is not the case, one need to change the basis to that one, before calling this function.
    """

    if U.type=='oper':
        inner = U.dag()*U_target
        part_idx = [0, 1, 3, 4]  # only computational subspace
        ptrace = 0
        for i in part_idx:
            ptrace += inner[i, i]
        dim = 4  # 2 qubits comp subspace       

        return np.real(((np.abs(ptrace))**2+dim*(1-L1))/(dim*(dim+1)))

    elif U.type=='super':
        kraus_form = qtp.to_kraus(U)
        dim=4 # 2 qubits in the computational subspace
        part_idx = [0, 1, 3, 4]  # only computational subspace
        psum=0
        for A_k in kraus_form:
            ptrace = 0
            inner = U_target_diffdims.dag()*A_k # otherwise dimension mismatch
            for i in part_idx:
                ptrace += inner[i, i]
            psum += (np.abs(ptrace))**2

        return np.real((dim*(1-L1) + psum) / (dim*(dim + 1)))


def pro_avfid_superoperator_compsubspace_phasecorrected(U,L1,phases):
    """
    Average process (gate) fidelity in the qubit computational subspace for two qutrits
    Leakage has to be taken into account, see Woods & Gambetta
    The phase is corrected with Z rotations considering both transmons as qubits. The correction is done perfectly.
    The function assumes that the computational subspace (:= the 4 energy levels chosen as the two qubits) is given by 
            the standard basis |0> /otimes |0>, |0> /otimes |1>, |1> /otimes |0>, |1> /otimes |1>.
            If this is not the case, one need to change the basis to that one, before calling this function.
    """

    Ucorrection = qtp.Qobj([[np.exp(-1j*np.deg2rad(phases[0])), 0, 0, 0, 0, 0, 0, 0, 0],
                     [0, np.exp(-1j*np.deg2rad(phases[1])), 0, 0, 0, 0, 0, 0, 0],
                     [0, 0, np.exp(-1j*np.deg2rad(phases[0])), 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, np.exp(-1j*np.deg2rad(phases[2])), 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[3]-phases[-1])), 0, 0, 0, 0],
                     [0, 0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[2])), 0, 0, 0],
                     [0, 0, 0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[0])), 0, 0],
                     [0, 0, 0, 0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[1])), 0],
                     [0, 0, 0, 0, 0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[0]))]],
                    type='oper',
                    dims=[[3, 3], [3, 3]])

    if U.type=='oper':
        U=Ucorrection*U
        inner = U.dag()*U_target
        part_idx = [0, 1, 3, 4]  # only computational subspace
        ptrace = 0
        for i in part_idx:
            ptrace += inner[i, i]
        dim = 4  # 2 qubits comp subspace       

        return np.real(((np.abs(ptrace))**2+dim*(1-L1))/(dim*(dim+1)))

    elif U.type=='super':
        U=qtp.to_super(Ucorrection)*U
        kraus_form = qtp.to_kraus(U)
        dim=4 # 2 qubits in the computational subspace
        part_idx = [0, 1, 3, 4]  # only computational subspace
        psum=0
        for A_k in kraus_form:
            ptrace = 0
            inner = U_target_diffdims.dag()*A_k # otherwise dimension mismatch
            for i in part_idx:
                ptrace += inner[i, i]
            psum += (np.abs(ptrace))**2

        return np.real((dim*(1-L1) + psum) / (dim*(dim + 1)))


def pro_avfid_superoperator_compsubspace_phasecorrected_onlystaticqubit(U,L1,phases):
    """
    Average process (gate) fidelity in the qubit computational subspace for two qutrits
    Leakage has to be taken into account, see Woods & Gambetta
    The phase is corrected with Z rotations considering both transmons as qubits. The correction is done perfectly.
    The function assumes that the computational subspace (:= the 4 energy levels chosen as the two qubits) is given by 
            the standard basis |0> /otimes |0>, |0> /otimes |1>, |1> /otimes |0>, |1> /otimes |1>.
            If this is not the case, one need to change the basis to that one, before calling this function.
    """

    Ucorrection = qtp.Qobj([[np.exp(-1j*np.deg2rad(phases[0])), 0, 0, 0, 0, 0, 0, 0, 0],
                     [0, np.exp(-1j*np.deg2rad(phases[0])), 0, 0, 0, 0, 0, 0, 0],
                     [0, 0, np.exp(-1j*np.deg2rad(phases[0])), 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, np.exp(-1j*np.deg2rad(phases[2])), 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[2])), 0, 0, 0, 0],
                     [0, 0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[2])), 0, 0, 0],
                     [0, 0, 0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[0])), 0, 0],
                     [0, 0, 0, 0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[0])), 0],
                     [0, 0, 0, 0, 0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[0]))]],
                    type='oper',
                    dims=[[3, 3], [3, 3]])

    if U.type=='oper':
        U=Ucorrection*U
        inner = U.dag()*U_target
        part_idx = [0, 1, 3, 4]  # only computational subspace
        ptrace = 0
        for i in part_idx:
            ptrace += inner[i, i]
        dim = 4  # 2 qubits comp subspace       

        return np.real(((np.abs(ptrace))**2+dim*(1-L1))/(dim*(dim+1)))

    elif U.type=='super':
        U=qtp.to_super(Ucorrection)*U
        kraus_form = qtp.to_kraus(U)
        dim=4 # 2 qubits in the computational subspace
        part_idx = [0, 1, 3, 4]  # only computational subspace
        psum=0
        for A_k in kraus_form:
            ptrace = 0
            inner = U_target_diffdims.dag()*A_k # otherwise dimension mismatch
            for i in part_idx:
                ptrace += inner[i, i]
            psum += (np.abs(ptrace))**2

        return np.real((dim*(1-L1) + psum) / (dim*(dim + 1)))


def leakage_from_superoperator(U):
    if U.type=='oper':
        """
        Calculates leakage by summing over all in and output states in the
        computational subspace.
            L1 = 1- 1/2^{number computational qubits} sum_i sum_j abs(|<phi_i|U|phi_j>|)**2
        The function assumes that the computational subspace (:= the 4 energy levels chosen as the two qubits) is given by 
            the standard basis |0> /otimes |0>, |0> /otimes |1>, |1> /otimes |0>, |1> /otimes |1>.
            If this is not the case, one need to change the basis to that one, before calling this function.
        """
        sump = 0
        for i in range(4):
            for j in range(4):
                bra_i = qtp.tensor(qtp.ket([i//2], dim=[3]),
                                   qtp.ket([i % 2], dim=[3])).dag()
                ket_j = qtp.tensor(qtp.ket([j//2], dim=[3]),
                                   qtp.ket([j % 2], dim=[3]))
                p = np.abs((bra_i*U*ket_j).data[0, 0])**2
                sump += p
        sump /= 4  # divide by dimension of comp subspace
        L1 = 1-sump
        return L1
    elif U.type=='super':
        """
        Calculates leakage by summing over all in and output states in the
        computational subspace.
            L1 = 1- 1/2^{number computational qubits} sum_i sum_j Tr(rho_{x'y'}C_U(rho_{xy}))
            where C_U is U in the channel representation
        The function assumes that the computational subspace (:= the 4 energy levels chosen as the two qubits) is given by 
            the standard basis |0> /otimes |0>, |0> /otimes |1>, |1> /otimes |0>, |1> /otimes |1>.
            If this is not the case, one need to change the basis to that one, before calling this function.
        """
        sump = 0
        for i in range(4):
            for j in range(4):
                ket_i = qtp.tensor(qtp.ket([i//2], dim=[3]),
                                   qtp.ket([i % 2], dim=[3])) #notice it's a ket
                rho_i=qtp.operator_to_vector(qtp.ket2dm(ket_i))
                ket_j = qtp.tensor(qtp.ket([j//2], dim=[3]),
                                   qtp.ket([j % 2], dim=[3]))
                rho_j=qtp.operator_to_vector(qtp.ket2dm(ket_j))
                p = (rho_i.dag()*U*rho_j).data[0, 0]
                sump += p
        sump /= 4  # divide by dimension of comp subspace
        sump=np.real(sump)
        L1 = 1-sump       
        return L1


def seepage_from_superoperator(U):
    """
    Calculates seepage by summing over all in and output states outside the
    computational subspace.
        L1 = 1- 1/2^{number non-computational states} sum_i sum_j abs(|<phi_i|U|phi_j>|)**2
        The function assumes that the computational subspace (:= the 4 energy levels chosen as the two qubits) is given by 
            the standard basis |0> /otimes |0>, |0> /otimes |1>, |1> /otimes |0>, |1> /otimes |1>.
            If this is not the case, one need to change the basis to that one, before calling this function.
    """
    if U.type=='oper':
        sump = 0
        for i_list in [[0,2],[1,2],[2,0],[2,1],[2,2]]:
            for j_list in [[0,2],[1,2],[2,0],[2,1],[2,2]]:
                bra_i = qtp.tensor(qtp.ket([i_list[0]], dim=[3]),
                                   qtp.ket([i_list[1]], dim=[3])).dag()
                ket_j = qtp.tensor(qtp.ket([j_list[0]], dim=[3]),
                                   qtp.ket([j_list[1]], dim=[3]))
                p = np.abs((bra_i*U*ket_j).data[0, 0])**2
                sump += p
        sump /= 5  # divide by number of non-computational states
        L1 = 1-sump
        return L1
    elif U.type=='super':
        sump = 0
        for i_list in [[0,2],[1,2],[2,0],[2,1],[2,2]]:
            for j_list in [[0,2],[1,2],[2,0],[2,1],[2,2]]:
                ket_i = qtp.tensor(qtp.ket([i_list[0]], dim=[3]),
                                   qtp.ket([i_list[1]], dim=[3]))
                rho_i=qtp.operator_to_vector(qtp.ket2dm(ket_i))
                ket_j = qtp.tensor(qtp.ket([j_list[0]], dim=[3]),
                                   qtp.ket([j_list[1]], dim=[3]))
                rho_j=qtp.operator_to_vector(qtp.ket2dm(ket_j))
                p = (rho_i.dag()*U*rho_j).data[0, 0]
                sump += p
        sump /= 5  # divide by number of non-computational states
        sump=np.real(sump)
        L1 = 1-sump
        return L1


def calc_population_02_state(U):
    """
    Calculates the population that escapes from |11> to |02>.
    Formula for unitary propagator:  population = |<02|U|11>|^2
    and similarly for the superoperator case.
        The function assumes that the computational subspace (:= the 4 energy levels chosen as the two qubits) is given by 
            the standard basis |0> /otimes |0>, |0> /otimes |1>, |1> /otimes |0>, |1> /otimes |1>.
            If this is not the case, one need to change the basis to that one, before calling this function.
    """
    if U.type=='oper':
        sump = 0
        for i_list in [[0,2]]:
            for j_list in [[1,1]]:
                bra_i = qtp.tensor(qtp.ket([i_list[0]], dim=[3]),
                                   qtp.ket([i_list[1]], dim=[3])).dag()
                ket_j = qtp.tensor(qtp.ket([j_list[0]], dim=[3]),
                                   qtp.ket([j_list[1]], dim=[3]))
                p = np.abs((bra_i*U*ket_j).data[0, 0])**2
                sump += p
        return np.real(sump)
    elif U.type=='super':
        sump = 0
        for i_list in [[0,2]]:
            for j_list in [[1,1]]:
                ket_i = qtp.tensor(qtp.ket([i_list[0]], dim=[3]),
                                   qtp.ket([i_list[1]], dim=[3]))
                rho_i=qtp.operator_to_vector(qtp.ket2dm(ket_i))
                ket_j = qtp.tensor(qtp.ket([j_list[0]], dim=[3]),
                                   qtp.ket([j_list[1]], dim=[3]))
                rho_j=qtp.operator_to_vector(qtp.ket2dm(ket_j))
                p = (rho_i.dag()*U*rho_j).data[0, 0]
                sump += p
        return np.real(sump)


def pro_avfid_superoperator(U):
    """
    Average process (gate) fidelity in the whole space for two qutrits
    The function assumes that the computational subspace (:= the 4 energy levels chosen as the two qubits) is given by 
            the standard basis |0> /otimes |0>, |0> /otimes |1>, |1> /otimes |0>, |1> /otimes |1>.
            If this is not the case, one need to change the basis to that one, before calling this function.
    """
    if U.type=='oper':
        ptrace = np.abs((U.dag()*U_target).tr())**2
        dim = 9  # dimension of the whole space
        return np.real((ptrace+dim)/(dim*(dim+1)))

    elif U.type=='super':
        return np.real(qtp.average_gate_fidelity(U,target=U_target_diffdims))


def pro_avfid_superoperator_phasecorrected(U,phases):
    """
    Average process (gate) fidelity in the whole space for two qutrits
    Qubit Z rotation and qutrit "Z" rotations are applied, taking into account the anharmonicity as well.
    The function assumes that the computational subspace (:= the 4 energy levels chosen as the two qubits) is given by 
            the standard basis |0> /otimes |0>, |0> /otimes |1>, |1> /otimes |0>, |1> /otimes |1>.
            If this is not the case, one need to change the basis to that one, before calling this function.
    This function is quite useless because we are always interested in the computational subspace only.
    """
    Ucorrection = qtp.Qobj([[np.exp(-1j*np.deg2rad(phases[0])), 0, 0, 0, 0, 0, 0, 0, 0],
                     [0, np.exp(-1j*np.deg2rad(phases[1])), 0, 0, 0, 0, 0, 0, 0],
                     [0, 0, np.exp(-1j*np.deg2rad(phases[4]-phases[-1])), 0, 0, 0, 0, 0, 0],
                     [0, 0, 0, np.exp(-1j*np.deg2rad(phases[2])), 0, 0, 0, 0, 0],
                     [0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[3]-phases[-1])), 0, 0, 0, 0],
                     [0, 0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[4]-phases[-1]+phases[2]-phases[0])), 0, 0, 0],
                     [0, 0, 0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[5])), 0, 0],
                     [0, 0, 0, 0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[5]+phases[1]-phases[0])), 0],
                     [0, 0, 0, 0, 0, 0, 0, 0, np.exp(-1j*np.deg2rad(phases[4]-phases[-1]+phases[5]-phases[0]))]],
                    type='oper',
                    dims=[[3, 3], [3, 3]])

    if U.type=='oper':
        U=Ucorrection*U
        ptrace = np.abs((U.dag()*U_target).tr())**2
        dim = 9  # dimension of the whole space
        return np.real((ptrace+dim)/(dim*(dim+1)))

    elif U.type=='super':
        U=qtp.to_super(Ucorrection)*U
        return np.real(qtp.average_gate_fidelity(U,target=U_target_diffdims))



def matrix_change_of_variables(H_0):
    # matrix diagonalizing H_0 as
    #       S.dag()*H_0*S = diagonal
    eigs,eigvectors=H_0.eigenstates()

    eigvectors_ordered_according2basis = []
    eigvectors_ordered_according2basis.append(eigvectors[0].full())   # 00 state
    eigvectors_ordered_according2basis.append(eigvectors[2].full())   # 01 state
    eigvectors_ordered_according2basis.append(eigvectors[5].full())   # 02 state
    eigvectors_ordered_according2basis.append(eigvectors[1].full())   # 10 state
    eigvectors_ordered_according2basis.append(eigvectors[4].full())   # 11 state
    eigvectors_ordered_according2basis.append(eigvectors[7].full())   # 12 state
    eigvectors_ordered_according2basis.append(eigvectors[3].full())   # 20 state
    eigvectors_ordered_according2basis.append(eigvectors[6].full())   # 21 state
    eigvectors_ordered_according2basis.append(eigvectors[8].full())   # 22 state

    S=np.hstack(eigvectors_ordered_according2basis)
    return S


def coupled_transmons_hamiltonian_new(w_q0, w_q1, alpha_q0, alpha_q1, J):
    """
    Hamiltonian of two coupled anharmonic transmons.
    Because the intention is to tune one qubit into resonance with the other,
    the number of levels is limited.
        q1 -> static qubit, 3-levels
        q0 -> fluxing qubit, 3-levels

    intended avoided crossing:
        11 <-> 02     (q1 is the first qubit and q0 the second one)

    N.B. the frequency of q0 is expected to be larger than that of q1
        w_q0 > w_q1
        and the anharmonicities alpha negative
    """

    H = w_q0 * n_q0 + w_q1 * n_q1 +  \
        1/2*alpha_q0*(a.dag()*a.dag()*a*a) + 1/2*alpha_q1*(b.dag()*b.dag()*b*b) +\
        J * (a.dag() + a) * (b + b.dag())
    H = H * (2*np.pi)
    return H


def calc_hamiltonian(amp,fluxlutman,noise_parameters_CZ):
    # all inputs should be given in terms of frequencies, i.e. without the 2*np.pi factor
    # instead, the output includes already that factor
    w_q0=fluxlutman.calc_amp_to_freq(amp,'01')
    w_q0_sweetspot=fluxlutman.calc_amp_to_freq(0,'01')
    w_q1=fluxlutman.calc_amp_to_freq(amp,'10')
    alpha_q0=fluxlutman.calc_amp_to_freq(amp,'02')-2*w_q0
    alpha_q1=noise_parameters_CZ.alpha_q1()
    J=fluxlutman.q_J2()/np.sqrt(2)
    w_bus=noise_parameters_CZ.w_bus()

    delta_q1=w_q1-w_bus
    delta_q0_sweetspot=(w_q0_sweetspot)-w_bus
    delta_q0=(w_q0)-w_bus
    J_temp = J / ((delta_q1+delta_q0_sweetspot)/(delta_q1*delta_q0_sweetspot)) * (delta_q1+delta_q0)/(delta_q1*delta_q0)

    H=coupled_transmons_hamiltonian_new(w_q0=w_q0, w_q1=w_q1, alpha_q0=alpha_q0, alpha_q1=alpha_q1, J=J_temp)
    return H


def verify_phicond(U):          # benchmark to check that cond phase is computed correctly. Benchmark succeeded
    # superoperator case
    if U.type == 'oper':
        U=qtp.to_super(U)
    def calc_phi(U,list):
        # lists of 4 matrix elements 0 or 1
        number=3*list[0]+list[1]+list[2]*27+list[3]*9
        phase=np.rad2deg(np.angle(U[number,number]))
        return phase

    phi_01=calc_phi(U,[0,1,0,0])
    phi_10=calc_phi(U,[1,0,0,0])
    phi_11=calc_phi(U,[1,1,0,0])
    phi_cond = (phi_11-phi_01-phi_10) % 360
    print(phi_cond)

    phi_01=-calc_phi(U,[0,0,0,1])
    phi_10=calc_phi(U,[1,0,0,1])
    phi_11=calc_phi(U,[1,1,0,1])
    phi_cond = (phi_11-phi_01-phi_10) % 360
    print(phi_cond)

    phi_01=-calc_phi(U,[0,0,1,0])
    phi_10=calc_phi(U,[0,1,1,0])
    phi_11=calc_phi(U,[1,1,1,0])
    phi_cond = (phi_11-phi_01-phi_10) % 360
    print(phi_cond)

    phi_01=-calc_phi(U,[0,0,1,1])
    phi_10=calc_phi(U,[0,1,1,1])
    phi_11=-calc_phi(U,[1,0,1,1])
    phi_cond = (phi_11-phi_01-phi_10) % 360
    print(phi_cond)
    return phi_cond



def simulate_quantities_of_interest_superoperator(tlist, c_ops, noise_parameters_CZ, fluxlutman,
                                    fluxbias_q1, amp,
                                    sim_step,
                                    verbose: bool=True):
    """
    Calculates the propagator and the quantities of interest from the propagator (either unitary or superoperator)

    Args:
        tlist (array): times in s, describes the x component of the
            trajectory to simulate (not actually used, we just use sim_step)
        sim_step(float): time between one point and another of amp
        c-ops (list of Qobj): time (in)dependent jump operators
        amp(array): amplitude in voltage describes the y-component of the trajectory to simulate
        fluxlutman,noise_parameters_CZ: instruments containing various parameters

    Returns
        phi_cond (float):   conditional phase (deg)
        L1      (float):    leakage
        L2      (float):    seepage
        avgatefid_pc (float):  average gate fidelity in full space, phase corrected
        avgatefid_compsubspace_pc (float):  average gate fidelity only in the computational subspace, phase corrected
        avgatefid_compsubspace (float):  average gate fidelity only in the computational subspace, not phase corrected,
                                         but taking into account the rotating frame of the two qutrits as qubits
        phase_q0 / q1 (float): single qubit phases in the rotating frame at the end of the pulse

    """

    H_0=calc_hamiltonian(0,fluxlutman,noise_parameters_CZ)   # computed at 0 amplitude
    # NOTE: parameters of H_0 could be not exactly e.g. the bare frequencies

    # We change the basis from the standard basis to the basis of eigenvectors of H_0
    # The columns of S are the eigenvectors of H_0, appropriately ordered
    if noise_parameters_CZ.dressed_compsub():
        S = qtp.Qobj(matrix_change_of_variables(H_0),dims=[[3, 3], [3, 3]])
    else:
        S = qtp.tensor(qtp.qeye(3),qtp.qeye(3))       # line here to quickly switch off the use of S
    H_0_diag = S.dag()*H_0*S

    #w_q0 = fluxlutman.q_freq_01()
    w_q0 = (H_0_diag[1,1]-H_0_diag[0,0]) / (2*np.pi)
    #w_q1 = fluxlutman.q_freq_10()
    w_q1 = (H_0_diag[3,3]-H_0_diag[0,0]) / (2*np.pi)

    # H_rotateaway = coupled_transmons_hamiltonian_new(w_q0=w_q0, w_q1=w_q1, 
    #                                                 alpha_q0=-2*w_q0, alpha_q1=-2*w_q1, J=0)

    w_q1_sweetspot = noise_parameters_CZ.w_q1_sweetspot()
    # Correction up to second order of the frequency due to flux noise, computed from w_q0(phi) = w_q0^sweetspot * sqrt(cos(pi * phi/phi_0))
    w_q1_biased = w_q1 - np.pi/2 * (w_q1_sweetspot**2/w_q1) * np.sqrt(1 - (w_q1**4/w_q1_sweetspot**4)) * fluxbias_q1 - \
                     - np.pi**2/2 * w_q1_sweetspot * (1+(w_q1**4/w_q1_sweetspot**4)) / (w_q1/w_q1_sweetspot)**3 * fluxbias_q1**2
                     # with sigma up to circa 1e-3 \mu\Phi_0 the second order is irrelevant
    correction_to_H = coupled_transmons_hamiltonian_new(w_q0=0, w_q1=np.real(w_q1_biased-w_q1), alpha_q0=0, alpha_q1=0, J=0)


    t0 = time.time()

    exp_L_total=1
    for i in range(len(amp)):
        H=calc_hamiltonian(amp[i],fluxlutman,noise_parameters_CZ) + correction_to_H
        H=S.dag()*H*S
        if c_ops != []:
            c_ops_temp=[]
            for c in range(len(c_ops)):
                if isinstance(c_ops[c],list):
                    c_ops_temp.append(c_ops[c][0]*c_ops[c][1][i])    # c_ops are already in the H_0 basis
                else:
                    c_ops_temp.append(c_ops[c])
            liouville_exp_t=(qtp.liouvillian(H,c_ops_temp)*sim_step).expm()
        else:
            liouville_exp_t=(-1j*H*sim_step).expm()
        exp_L_total=liouville_exp_t*exp_L_total

    t1 = time.time()
    #print('\n alternative propagator',t1-t0)


    U_final = exp_L_total
    #U_final=rotating_frame_transformation_new(U_final, fluxlutman.cz_length(), H_0_diag)

    phases = phases_from_superoperator(U_final)         # order is phi_00, phi_01, phi_10, phi_11, phi_02, phi_20, phi_cond
    phi_cond = phases[-1]
    L1 = leakage_from_superoperator(U_final)
    population_02_state = calc_population_02_state(U_final)
    L2 = seepage_from_superoperator(U_final)
    avgatefid = pro_avfid_superoperator_phasecorrected(U_final,phases)
    avgatefid_compsubspace = pro_avfid_superoperator_compsubspace_phasecorrected(U_final,L1,phases)     # leakage has to be taken into account, see Woods & Gambetta
    #print('avgatefid_compsubspace',avgatefid_compsubspace)

    
    
    #H_twoqubits = coupled_transmons_hamiltonian_new(w_q0=w_q0, w_q1=w_q1, 
    #                                                alpha_q0=-2*w_q0, alpha_q1=-2*w_q1, J=0)
    #U_final_new = rotating_frame_transformation_new(U_final, fluxlutman.cz_length(), H_twoqubits)         ### old method rotating away also the phase of the |2> state

    t = tlist[-1]+sim_step
    U_final_new = correct_reference(U=U_final,w_q1=w_q1,w_q0=w_q0,t=t)

    ### Script to check that we are correctly removing the single qubit phases in the rotating frame
    # cz_length = fluxlutman.cz_length()
    # U_check = (1j*H_twoqubits*cz_length).expm() * (-1j*H_0_diag*cz_length).expm()
    # phases_check = phases_from_superoperator(U_check)
    # print(phases_check)

    
    avgatefid_compsubspace_notphasecorrected = pro_avfid_superoperator_compsubspace(U_final_new,L1)
    # NOTE: a single qubit phase off by 30 degrees costs 5.5% fidelity

    ### Script to check that leakage and phi_cond are not affected by the phase correction, as it should be
    # L1_bis = leakage_from_superoperator(U_final_new)
    # phi_cond_bis = phases_from_superoperator(U_final_new)[-1]
    # print('leakage',L1-L1_bis)
    # print('phi_cond',phi_cond-phi_cond_bis)

    phases = phases_from_superoperator(U_final_new)         # order is phi_00, phi_01, phi_10, phi_11, phi_02, phi_20, phi_cond
    phase_q0 = (phases[1]-phases[0]) % 360
    phase_q1 = (phases[2]-phases[0]) % 360


    # We now correct only for the phase of qubit left (q1), in the rotating frame
    avgatefid_compsubspace_pc_onlystaticqubit = pro_avfid_superoperator_compsubspace_phasecorrected_onlystaticqubit(U_final_new,L1,phases)
    

    return {'phi_cond': phi_cond, 'L1': L1, 'L2': L2, 'avgatefid_pc': avgatefid,
            'avgatefid_compsubspace_pc': avgatefid_compsubspace, 'phase_q0': phase_q0, 'phase_q1': phase_q1,
            'avgatefid_compsubspace': avgatefid_compsubspace_notphasecorrected,
            'avgatefid_compsubspace_pc_onlystaticqubit': avgatefid_compsubspace_pc_onlystaticqubit, 'population_02_state': population_02_state,
            'U_final_new': U_final_new}


def gaussian(x,mean,sigma):    # normalized Gaussian
    return 1/np.sqrt(2*np.pi)/sigma * np.exp(-(x-mean)**2/(2*sigma**2))


## phases need to be averaged carefully, e.g. average of 45 and 315 degrees is 0, not 180
def average_phases(phases,weights):
    # phases has to be passed in degrees
    sines=np.sin(np.deg2rad(phases))
    cosines=np.cos(np.deg2rad(phases))
    # we separately average sine and cosine
    av_sines=np.average(sines,weights=weights)
    av_cosines=np.average(cosines,weights=weights)
    # need to normalize
    av_sines=av_sines/(av_sines**2+av_cosines**2)
    av_cosines=av_cosines/(av_sines**2+av_cosines**2)
    angle_temp_sin = np.arcsin(av_sines)
    angle_temp_cos = np.arccos(av_cosines)
    # then we combine them to give the unique angle with such sine and cosine
    # To avoid problems with the discontinuities of arcsin and arccos, we choose to use the average which is not very close to such discontinuities
    if np.abs(angle_temp_sin)<np.pi/3:
        if av_cosines >= 0:
            angle = angle_temp_sin
        else:
            angle = np.pi-angle_temp_sin
    elif np.abs(angle_temp_cos-np.pi/2)<np.pi/3:
        if av_sines >= 0:
            angle = angle_temp_cos
        else:
            angle = 2*np.pi-angle_temp_cos
    else:
        logging.warning('Something wrong with averaging the phases.')
    return np.rad2deg(angle) % 360


def concatenate_CZpulse_and_Zrotations(Z_rotations_length,sim_step,tlist):
    if Z_rotations_length != 0:
        tlist_singlequbitrotations = np.arange(0,Z_rotations_length, sim_step)
        tlist = np.concatenate([tlist,tlist_singlequbitrotations+sim_step+tlist[-1]])
    return tlist



def function_to_parallelize(arglist):
    # list = [samplepoint_q0,samplepoint_q1,fluxlutman,noise_parameters_CZ,fitted_stepresponse_ty]
    fluxbias_q0 = arglist[0]
    fluxbias_q1 = arglist[1]
    fluxlutman = arglist[2]
    noise_parameters_CZ = arglist[3]
    fitted_stepresponse_ty = arglist[4]


    sim_step=1/fluxlutman.sampling_rate()
    subdivisions_of_simstep=4      # 4 is a good one, corresponding to a time step of 0.1 ns
    sim_step_new=sim_step/subdivisions_of_simstep      # waveform is generated according to sampling rate of AWG,
                                                       # but we can use a different step for simulating the time evolution
    tlist = (np.arange(0, fluxlutman.cz_length(),
                       sim_step))
    
    eps_i = fluxlutman.calc_amp_to_eps(0, state_A='11', state_B='02')
    theta_i = wfl.eps_to_theta(eps_i, g=fluxlutman.q_J2())           # Beware theta in radian!


    if not fluxlutman.czd_double_sided():
        thetawave = wfl.martinis_flux_pulse(
            length=fluxlutman.cz_length(),
            lambda_2=fluxlutman.cz_lambda_2(),
            lambda_3=fluxlutman.cz_lambda_3(),
            theta_i=theta_i,
            theta_f=np.deg2rad(fluxlutman.cz_theta_f()),
            sampling_rate=fluxlutman.sampling_rate())    # return in terms of theta
        epsilon = wfl.theta_to_eps(thetawave, fluxlutman.q_J2())
        amp = fluxlutman.calc_eps_to_amp(epsilon, state_A='11', state_B='02')
                 # transform detuning frequency to (positive) amplitude
    else:
        amp = get_f_pulse_double_sided(fluxlutman,theta_i)
       

    # For better accuracy in simulations, redefine f_pulse and amp in terms of sim_step_new.
    # We split here below in two cases to keep into account that certain times net-zero is one AWG time-step longer than the conventional with the same pulse length
    if len(tlist) == len(amp):
        tlist_temp=np.concatenate((tlist,np.array([fluxlutman.cz_length()])))
        tlist_new = (np.arange(0, fluxlutman.cz_length(),
                       sim_step_new))
    else:
        tlist_temp=np.concatenate((tlist,np.array([fluxlutman.cz_length(),fluxlutman.cz_length()+sim_step])))
        tlist_new = (np.arange(0, fluxlutman.cz_length()+sim_step,
                       sim_step_new))
    # # account for Z rotations
    # tlist_temp = concatenate_CZpulse_and_Zrotations(noise_parameters_CZ.Z_rotations_length(),sim_step,tlist_temp)
    # tlist_new = concatenate_CZpulse_and_Zrotations(noise_parameters_CZ.Z_rotations_length(),sim_step_new,tlist_new)

    amp_temp=np.concatenate((amp,np.array([amp[0]])))
    amp_interp=interp1d(tlist_temp,amp_temp)
    amp=amp_interp(tlist_new)

    if noise_parameters_CZ.Z_rotations_length() != 0:
        tlist_singlequbitrotations = np.arange(0,noise_parameters_CZ.Z_rotations_length(),sim_step_new)
        amp = np.concatenate([amp,np.zeros(len(tlist_singlequbitrotations))+amp[0]])
        tlist_new = concatenate_CZpulse_and_Zrotations(noise_parameters_CZ.Z_rotations_length(),sim_step_new,tlist_new)

    # plot(x_plot_vec=[np.array(tlist_new)*1e9],y_plot_vec=[amp],
    #          title='Pulse with single qubit rotations',
    #            xlabel='Time (ns)',ylabel='Amplitude (volts)')


    amp=amp*noise_parameters_CZ.voltage_scaling_factor()       # recommended to change discretely the scaling factor


    if noise_parameters_CZ.distortions():
        fitted_stepresponse_ty_temp=np.concatenate([np.zeros(1),fitted_stepresponse_ty[1]])    # to make gradient work properly
        impulse_response_temp=np.gradient(fitted_stepresponse_ty_temp)
        impulse_response= np.delete(impulse_response_temp,-1)     # to have t and y of the same length for interpolation

        # plot(x_plot_vec=[np.array(fitted_stepresponse_ty[0])*1e9],y_plot_vec=[fitted_stepresponse_ty[1]],
        #       title='Step response',
        #       xlabel='Time (ns)')
        # plot(x_plot_vec=[np.array(fitted_stepresponse_ty[0])*1e9],y_plot_vec=[impulse_response],
        #       title='Impulse response',
        #       xlabel='Time (ns)')

        # use interpolation to be sure that amp and impulse_response have the same delta_t separating two values
        amp_interp = interp1d(tlist_new,amp)
        impulse_response_interp = interp1d(fitted_stepresponse_ty[0],impulse_response)

        tlist_convol1 = tlist_new
        tlist_convol2 = np.arange(0, fitted_stepresponse_ty[0][-1],
                           sim_step_new)
        amp_convol = amp_interp(tlist_convol1)
        impulse_response_convol = impulse_response_interp(tlist_convol2)

        convolved_amp=scipy.signal.convolve(amp_convol,impulse_response_convol)/sum(impulse_response_convol)

        # plot(x_plot_vec=[tlist_convol1*1e9,np.arange(np.size(convolved_amp))*sim_step_new*1e9],
        #       y_plot_vec=[amp_convol, convolved_amp],
        #       title='Pulse_length= {} ns'.format(fluxlutman.cz_length()*1e9),
        #       xlabel='Time (ns)',ylabel='Amplitude (V)',legend_labels=['Ideal','Distorted'])

        amp_final=convolved_amp[0:np.size(tlist_convol1)]    # consider only amp during the gate time

        # plot(x_plot_vec=[tlist_convol1*1e9],
        #       y_plot_vec=[amp_convol, amp_final],
        #       title='Pulse_length= {} ns'.format(fluxlutman.cz_length()*1e9),
        #       xlabel='Time (ns)',ylabel='Amplitude (V)',legend_labels=['Ideal','Distorted'])

    else:
        amp_final=amp



    ### the fluxbias_q0 affects the pulse shape after the distortions have been taken into account
    if not fluxlutman.czd_double_sided():
        omega_0 = fluxlutman.calc_amp_to_freq(0,'01')

        f_pulse = fluxlutman.calc_amp_to_freq(amp_final,'01')
        f_pulse = np.clip(f_pulse,a_min=None,a_max=omega_0)                    # necessary otherwise the sqrt below gives nan

        # Correction up to second order of the frequency due to flux noise, computed from w_q0(phi) = w_q0^sweetspot * sqrt(cos(pi * phi/phi_0))
        f_pulse_final = f_pulse - np.pi/2 * (omega_0**2/f_pulse) * np.sqrt(1 - (f_pulse**4/omega_0**4)) * fluxbias_q0 - \
                              - np.pi**2/2 * omega_0 * (1+(f_pulse**4/omega_0**4)) / (f_pulse/omega_0)**3 * fluxbias_q0**2
                              # with sigma up to circa 1e-3 \mu\Phi_0 the second order is irrelevant

        amp_final = fluxlutman.calc_freq_to_amp(f_pulse_final,state='01')

    else:
        half_length = int(np.size(amp_final)/2)
        amp_A = amp_final[0:half_length]                # positive and negative parts
        amp_B = amp_final[half_length:]


        omega_0 = fluxlutman.calc_amp_to_freq(0,'01')

        f_pulse_A = fluxlutman.calc_amp_to_freq(amp_A,'01')
        f_pulse_A = np.clip(f_pulse_A,a_min=None,a_max=omega_0)


        f_pulse_A = f_pulse_A - np.pi/2 * (omega_0**2/f_pulse_A) * np.sqrt(1 - (f_pulse_A**4/omega_0**4)) * fluxbias_q0 - \
                              - np.pi**2/2 * omega_0 * (1+(f_pulse_A**4/omega_0**4)) / (f_pulse_A/omega_0)**3 * fluxbias_q0**2
                              # with sigma up to circa 1e-3 \mu\Phi_0 the second order is irrelevant
        amp_A = fluxlutman.calc_freq_to_amp(f_pulse_A,state='01')


        f_pulse_B = fluxlutman.calc_amp_to_freq(amp_B,'01')
        f_pulse_B = np.clip(f_pulse_B,a_min=None,a_max=omega_0)

        f_pulse_B = f_pulse_B - np.pi/2 * (omega_0**2/f_pulse_B) * np.sqrt(1 - (f_pulse_B**4/omega_0**4)) * fluxbias_q0 * (-1) - \
                      - np.pi**2/2 * omega_0 * (1+(f_pulse_B**4/omega_0**4)) / (f_pulse_B/omega_0)**3 * fluxbias_q0**2
                      # with sigma up to circa 1e-3 \mu\Phi_0 the second order is irrelevant
        amp_B = fluxlutman.calc_freq_to_amp(f_pulse_B,state='01',positive_branch=False)


        amp_final = np.concatenate([amp_A, amp_B])
        f_pulse_final=np.concatenate([f_pulse_A, f_pulse_B])



    ### Script to plot the waveform
    # plot(x_plot_vec=[tlist_new*1e9],
    #           y_plot_vec=[f_pulse_final/1e9],
    #           title='Freq. of fluxing qubit during pulse',
    #           xlabel='Time (ns)',ylabel='Freq. (GHz)',legend_labels=['omega_B(t)'])


    ### Script to check how the pulse is affected by the flux bias
    # plot(x_plot_vec=[tlist_new*1e9],
    #           y_plot_vec=[f_pulse-f_pulse_final],
    #           title='Diff. of freq. of fluxing qubit w/o flux bias',
    #           xlabel='Time (ns)',ylabel='Freq. (GHz)',legend_labels=['diff'])



    # Noise
    T1_q0 = noise_parameters_CZ.T1_q0()
    T1_q1 = noise_parameters_CZ.T1_q1()
    T2_q0_sweetspot = noise_parameters_CZ.T2_q0_sweetspot()                   # deprecated
    T2_q0_interaction_point = noise_parameters_CZ.T2_q0_interaction_point()   # deprecated
    T2_q0_amplitude_dependent = noise_parameters_CZ.T2_q0_amplitude_dependent()
    T2_q1 = noise_parameters_CZ.T2_q1()

    def Tphi_from_T1andT2(T1,T2):
        return 1/(-1/(2*T1)+1/T2)

    if T2_q0_sweetspot != 0:
        Tphi01_q0_sweetspot=Tphi_from_T1andT2(T1_q0,T2_q0_sweetspot)
    else:
        Tphi01_q0_sweetspot=0
    if T2_q0_interaction_point != 0:
        Tphi01_q0_interaction_point=Tphi_from_T1andT2(T1_q0,T2_q0_interaction_point)
    else:
        Tphi01_q0_interaction_point=0
    # Tphi01=Tphi12=2*Tphi02
    if T2_q1 != 0:
        if T1_q1 != 0:
            Tphi01_q1 = Tphi_from_T1andT2(T1_q1,T2_q1)
        else:
            Tphi01_q1 = T2_q1
    else:
        Tphi01_q1 = 0



    if T2_q0_amplitude_dependent[0] != -1:    # preferred way to handle T2 amplitude-dependent

        def expT2(x,gc,amp,tau):
            return gc+gc*amp*np.exp(-x/tau)         # formula used to fit the experimental data

        T2_q0_vec=expT2(f_pulse_final,T2_q0_amplitude_dependent[0],T2_q0_amplitude_dependent[1],T2_q0_amplitude_dependent[2])
        if T1_q0 != 0:
            Tphi01_q0_vec = Tphi_from_T1andT2(T1_q0,T2_q0_vec)
        else:
            Tphi01_q0_vec = T2_q0_vec     # in the case where we don't want T1 and we are inputting Tphi and not T2

        c_ops = c_ops_amplitudedependent(T1_q0,T1_q1,Tphi01_q0_vec,Tphi01_q1)

    else:                                      # mode where the collapse operators are time-independent, and possibly are 0
        if T1_q1 != 0:
            c_ops=jump_operators(T1_q0,T1_q1)
        else:
            c_ops=[]



    qoi = simulate_quantities_of_interest_superoperator(
        tlist=tlist_new, c_ops=c_ops, noise_parameters_CZ=noise_parameters_CZ, 
        fluxlutman=fluxlutman, fluxbias_q1=fluxbias_q1, amp=amp_final,
        sim_step=sim_step_new, verbose=False)

    cost_func_val = -np.log10(1-qoi['avgatefid_compsubspace_pc'])    # this is actually not used in the following



    quantities_of_interest = [cost_func_val, qoi['phi_cond'], qoi['L1']*100, qoi['L2']*100, qoi['avgatefid_pc']*100, 
                 qoi['avgatefid_compsubspace_pc']*100, qoi['phase_q0'], qoi['phase_q1'], 
                 qoi['avgatefid_compsubspace']*100, qoi['avgatefid_compsubspace_pc_onlystaticqubit']*100, qoi['population_02_state']*100]
    qoi_np=np.array(quantities_of_interest)
    U_final_np = qoi['U_final_new']            # note that this is the propagator in the rotating frame

    return [qoi_np, U_final_np]



def get_f_pulse_double_sided(fluxlutman,theta_i):

        thetawave_A = wfl.martinis_flux_pulse(
            length=fluxlutman.cz_length()*fluxlutman.czd_length_ratio(),
            lambda_2=fluxlutman.cz_lambda_2(),
            lambda_3=fluxlutman.cz_lambda_3(),
            theta_i=theta_i,
            theta_f=np.deg2rad(fluxlutman.cz_theta_f()),
            sampling_rate=fluxlutman.sampling_rate())    # return in terms of theta
        epsilon_A = wfl.theta_to_eps(thetawave_A, fluxlutman.q_J2())
        amp_A = fluxlutman.calc_eps_to_amp(epsilon_A, state_A='11', state_B='02')
                     # transform detuning frequency to positive amplitude
        

        # Generate the second CZ pulse. If the params are np.nan, default
        # to the main parameter
        if not np.isnan(fluxlutman.czd_theta_f()):
            d_theta_f = fluxlutman.czd_theta_f()
        else:
            d_theta_f = fluxlutman.cz_theta_f()

        if not np.isnan(fluxlutman.czd_lambda_2()):
            d_lambda_2 = fluxlutman.czd_lambda_2()
        else:
            d_lambda_2 = fluxlutman.cz_lambda_2()
        if not np.isnan(fluxlutman.czd_lambda_3()):
            d_lambda_3 = fluxlutman.czd_lambda_3()
        else:
            d_lambda_3 = fluxlutman.cz_lambda_3()

        thetawave_B = wfl.martinis_flux_pulse(
            length=fluxlutman.cz_length()*(1-fluxlutman.czd_length_ratio()),
            lambda_2=d_lambda_2,
            lambda_3=d_lambda_3,
            theta_i=theta_i,
            theta_f=np.deg2rad(d_theta_f),
            sampling_rate=fluxlutman.sampling_rate())    # return in terms of theta
        epsilon_B = wfl.theta_to_eps(thetawave_B, fluxlutman.q_J2())
        amp_B = fluxlutman.calc_eps_to_amp(epsilon_B, state_A='11', state_B='02', positive_branch=False)
                     # transform detuning frequency to negative amplitude

        # N.B. No amp scaling and offset present
        amp = np.concatenate([amp_A, amp_B])
        return amp





class CZ_trajectory_superoperator(det.Soft_Detector):
    def __init__(self, fluxlutman, noise_parameters_CZ, fitted_stepresponse_ty):
        """
        Detector for simulating a CZ trajectory.
        Args:
            fluxlutman (instr): an instrument that contains the parameters
                required to generate the waveform for the trajectory, and the hamiltonian as well.
            noise_parameters_CZ: instrument that contains the noise parameters, plus some more
            fitted_stepresponse_ty: list of two elements, corresponding to the time t 
                                    and the step response in volts along the y axis
        """
        super().__init__()
        self.value_names = ['Cost func', 'Cond phase', 'L1', 'L2', 'avgatefid_pc', 'avgatefid_compsubspace_pc',
                            'phase_q0', 'phase_q1', 'avgatefid_compsubspace', 'avgatefid_compsubspace_pc_onlystaticqubit', 'population_02_state']
        self.value_units = ['a.u.', 'deg', '%', '%', '%', '%', 'deg', 'deg', '%', '%', '%']
        self.fluxlutman = fluxlutman
        self.noise_parameters_CZ = noise_parameters_CZ
        self.fitted_stepresponse_ty=fitted_stepresponse_ty      # list of 2 elements: stepresponse (=y)
                                                                # as a function of time (=t)


    def acquire_data_point(self, **kw):

        ### Discretize average (integral) over a Gaussian distribution
        mean = 0

        qoi_plot = list()    # used to verify convergence properties. If len(n_sampling_gaussian_vec)==1, it is useless
        n_sampling_gaussian_vec = [11]  # 11 guarantees excellent convergence. We choose it odd so that the central point of the Gaussian is included.
                                        # ALWAYS choose it odd
        for n_sampling_gaussian in n_sampling_gaussian_vec:
            # If sigma=0 there's no need for sampling
            if self.noise_parameters_CZ.sigma() != 0:
                samplingpoints_gaussian = np.linspace(-5*self.noise_parameters_CZ.sigma(),5*self.noise_parameters_CZ.sigma(),n_sampling_gaussian)    # after 5 sigmas we cut the integral
                delta_x = samplingpoints_gaussian[1]-samplingpoints_gaussian[0]
                values_gaussian = gaussian(samplingpoints_gaussian,mean,self.noise_parameters_CZ.sigma())
            else:
                samplingpoints_gaussian = np.array([0])
                delta_x = 1
                values_gaussian = np.array([1])



            ### Parallelize computation for averaging
            input_to_parallelize = []
            weights=[]
            for j_q0 in range(len(samplingpoints_gaussian)):
                for j_q1 in range(len(samplingpoints_gaussian)):

                    if self.noise_parameters_CZ.sigma() != 0:
                        input_point = [samplingpoints_gaussian[j_q0],samplingpoints_gaussian[j_q1],self.fluxlutman,self.noise_parameters_CZ,self.fitted_stepresponse_ty]

                        weights.append(samplingpoints_gaussian[j_q0] * samplingpoints_gaussian[j_q1] * delta_x**2)
                    else:
                        input_point = [0,0,self.fluxlutman,self.noise_parameters_CZ,self.fitted_stepresponse_ty]
 
                        weights=[1]
                    input_to_parallelize.append(input_point)

            weights = np.array(weights)



            x_list = input_to_parallelize
            y_list_of_lists = map_jobqueue(function_to_parallelize, x_list)

            y_list_of_lists = np.array(y_list_of_lists)

            qoi_vec = y_list_of_lists[:,0]
            U_final_vec = y_list_of_lists[:,1]
            # def f_trial(x):
            #     return x**2
            # x_list = np.linspace(0,5,1)
            # y_list = map_jobqueue(f_trial, x_list)
            # print(y_list)



            qoi_average = np.zeros(len(qoi_vec[0,:]))
            for index in [2,3,4,8,10]:    # 4 is not trustable here, and we don't care anyway
                qoi_average[index] = np.average(np.array(qoi_vec)[:,index], weights=weights)


            for index in [1,6,7]:
                qoi_average[index]=average_phases(np.array(qoi_vec)[:,index], weights=weights)


            # The correction for avgatefid_pc should be always the same. We choose to correct an angle equal to the average angle
            phases=[0,qoi_average[6],qoi_average[7],qoi_average[6]+qoi_average[7],0,0,0]
            average=0
            average_partial=0
            for j in range(len(U_final_vec)):
                U_final=U_final_vec[j]
                L1=leakage_from_superoperator(U_final)
                avgatefid_compsubspace_pc=pro_avfid_superoperator_compsubspace_phasecorrected(U_final,L1,phases)
                avgatefid_compsubspace_partial=pro_avfid_superoperator_compsubspace_phasecorrected_onlystaticqubit(U_final,L1,phases)
                average+=avgatefid_compsubspace_pc * weights[j]
                average_partial+=avgatefid_compsubspace_partial * weights[j]
            qoi_average[5]=average*100
            qoi_average[9]=average_partial*100

            qoi_average[0] = (-np.log10(1-qoi_average[5]/100))    # we want log of the average and not average of the log

            qoi_plot.append(qoi_average)

        qoi_plot = np.array(qoi_plot)

        
        ### Plot to study the convergence properties of averaging over a Gaussian
        # for i in range(len(qoi_plot[0])):
        #     plot(x_plot_vec=[n_sampling_gaussian_vec],
              #             y_plot_vec=[qoi_plot[:,i]],
              #             title='Study of convergence of average',
              #             xlabel='n_sampling_gaussian points',ylabel=self.value_names[i])


        return qoi_plot[0,0], qoi_plot[0,1], qoi_plot[0,2], qoi_plot[0,3], qoi_plot[0,4], qoi_plot[0,5], qoi_plot[0,6], \
               qoi_plot[0,7], qoi_plot[0,8], qoi_plot[0,9], qoi_plot[0,10]



    
