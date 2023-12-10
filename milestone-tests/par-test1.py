"""
Used in benchmarking communication methods between processes

"""


from mpi4py import MPI
import time


SIZE_DATA = 1000


comm = MPI.COMM_WORLD
rank = comm.Get_rank()

start_time = time.time()

if rank == 0:
    # Process 0 sends data
    data = list(range(SIZE_DATA))
    comm.send(data, dest=1, tag=11)
    print("Process 0 sent data to Process 1")

elif rank == 1:
    # Process 1 receives data
    recv_data = comm.recv(source=0, tag=11)
    print(f"Data communicated in {time.time() - start_time} seconds")
