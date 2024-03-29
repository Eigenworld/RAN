import torch
import torch.nn as nn
from torch.nn import Linear
from torch_scatter import scatter_add
from torch_geometric.nn.conv import MessagePassing
from torch_geometric.utils import add_remaining_self_loops
from torch_geometric.nn.inits import uniform


class DAD_Conv(MessagePassing):
    def __init__(self, in_channels, out_channels, K=1, cached=True, bias=True,
                 improve=False, **kwargs):
        super(DAD_Conv, self).__init__(aggr='add', **kwargs)

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.K = K
        self.improve = improve
        self.cached = cached

        self.lin = Linear(in_channels, out_channels, bias=bias)

        self.reset_parameters()
        
    '''def reset_parameters(self):
        gain = nn.init.calculate_gain('relu')
        nn.init.xavier_uniform_(self.lin.weight, gain=gain)
        nn.init.zeros_(self.lin.bias)
        self.cached_result = None
        self.cached_num_edges = None'''

    '''def reset_parameters(self):
        uniform(self.in_channels, self.weight)
        uniform(self.in_channels, self.bias)'''
        
    def reset_parameters(self):
        print('hola!')
        self.lin.reset_parameters()
        self.cached_result = None
        self.cached_num_edges = None

    def forward(self, x, edge_index, edge_weight=None):
        """"""
        if self.cached and self.cached_result is not None:
            if edge_index.size(1) != self.cached_num_edges:
                raise RuntimeError(
                    'Cached {} number of edges, but found {}. Please '
                    'disable the caching behavior of this layer by removing '
                    'the `cached=True` argument in its constructor.'.format(
                        self.cached_num_edges, edge_index.size(1)))

        

        if not self.cached or self.cached_result is None:
            self.cached_num_edges = edge_index.size(1)
            edge_index, norm = self.My_norms(edge_index, x.size(0), edge_weight, self.improve
                                            , dtype=x.dtype)
            for k in range(self.K):
                x = self.propagate(edge_index, x=x, norm=norm)
                
            self.cached_result = x

        if self.cached:
            x = self.lin(self.cached_result)

        return x
    
    def My_norms(self, edge_index, num_nodes, edge_weight=None, improved=False,
             dtype=None):
        if edge_weight is None:
            edge_weight = torch.ones((edge_index.size(1), ), dtype=dtype,
                                     device=edge_index.device)

        fill_value = 1 if not improved else 2
        edge_index, edge_weight = add_remaining_self_loops(
            edge_index, edge_weight, fill_value, num_nodes)

        row, col = edge_index
        deg = scatter_add(edge_weight, row, dim=0, dim_size=num_nodes)
        deg_inv_sqrt = deg.pow(-0.5)
        deg_inv_sqrt[deg_inv_sqrt == float('inf')] = 0

        return edge_index, deg_inv_sqrt[col] * edge_weight*deg_inv_sqrt[row] 
        
    def message(self, x_j, norm):
        return norm.view(-1, 1) * x_j

    def __repr__(self):
        return '{}({}, {}, K={})'.format(self.__class__.__name__,
                                         self.in_channels, self.out_channels,
                                         self.K)