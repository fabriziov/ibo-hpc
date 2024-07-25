from .experiment import BenchmarkExperiment
from ..benchmarks import BenchmarkFactory
from ..optimizers import OptimizerFactory
from copy import deepcopy
import json
import numpy as np
from ConfigSpace import CategoricalHyperparameter
import os
import numpy as np

class NASBench101InteractiveExperiment(BenchmarkExperiment):

    def __init__(self, optimizer_name, intervention_idx=[-1], task='cifar10') -> None:
        self._intervention_idx = intervention_idx
        self.benchmark_name = 'nas101'
        self.benchmark_config = {
            'task': task
        }
        benchmark = BenchmarkFactory.get_benchmark(self.benchmark_name, 
                                                        self.benchmark_config)

        self._optimizer_name = optimizer_name
        self.optimizer_config = self.get_optimizer_config(benchmark)
        optimizer = OptimizerFactory.get_optimizer(optimizer_name, self.optimizer_config)   
        super().__init__(benchmark, optimizer)     

    def run(self):
        # register intervention
        if self._optimizer_name == 'pc':
            interventions, iterations = self.get_pc_interventions()
            self.optimizer.intervene(interventions, iters=iterations)
        elif self._optimizer_name == 'bopro':
            interventions = self.get_bopro_intervention()
            self.optimizer.intervene(interventions)
        else:
            interventions = self.get_pibo_intervention()
            self.optimizer.intervene(interventions)
        config, performance = self.optimizer.optimize()
        if self._optimizer_name == 'pc':
            processed_config = {}
            for name, idx in config.items():
                param_def = self.benchmark.search_space.search_space_definition[name]
                processed_config[name] = param_def['allowed'][int(idx)]
            config = processed_config
        print((config, performance))

    def evaluate_config(self, cfg, budget=None):
        test_cfg = cfg
        if self._optimizer_name == 'pc':
            ops = self.benchmark.search_space.operations
            cfg_copy = deepcopy(cfg)
            for key, val in cfg.items():
                if key.startswith('o_') or key.startswith('Op'):
                    cfg_copy[key] = ops[int(val)]
            test_cfg = cfg_copy
        if self.benchmark is not None and self.benchmark.search_space.is_valid(test_cfg):
            res = self.benchmark.query(test_cfg, budget)
            return res
        
    def get_optimizer_config(self, benchmark):
        assert benchmark is not None, 'Something went wrong instantiating the benchmark'
        if self._optimizer_name == 'pibo':
            return {
                'objective': self.evaluate_config,
                'search_space': benchmark.search_space,
                'n_trials': 2000
            }
        elif self._optimizer_name == 'bopro':
            self.setup_bopro_json(benchmark)
            return {
                'objective': self.evaluate_config,
                'search_space': benchmark.search_space,
                'exp_json': self._bopro_file_name
            }
        elif self._optimizer_name == 'pc': 
            return {
                'objective': self.evaluate_config,
                'search_space': benchmark.search_space,
                'iterations': 100,
                'samples_per_iter': 20,
                'use_eic': False,
                'eic_samplings': 20,
                'interaction_dist_sample_decay': 0.9,
            }
        else:
            raise ValueError(f'No such optimizer: {self._optimizer_name}')

    def get_pc_interventions(self):
        """
            load intervention
        """
        #good_int = pd.read_csv('./interventions/nas101_cifar10_good.csv', index_col=0)
        #bad_int = pd.read_csv('./interventions/nas101_cifar10_bad.csv', index_col=0)
        with open('./interventions/nas101_cifar10.json', 'r') as f:
            ints_json = json.load(f)

        interactions = []
        iterations = []
        for interaction_definition in ints_json:
            interaction = {}
            it = interaction_definition['iteration']
            new_matrix = np.zeros((7, 7))
            architecture = interaction_definition['intervention']
            if architecture is not None:
                if isinstance(architecture, dict):
                    interactions.append(architecture)
                else:
                    new_matrix[np.triu_indices(7, 1)] = architecture
                    tri_inds1, tri_inds2 = np.triu_indices(7, 1)
                    for i, j in zip(tri_inds1, tri_inds2):
                        edge_name = f'e_{i}_{j}'
                        interaction[edge_name] = new_matrix[i, j]
                    interactions.append(interaction)
            else:
                interactions.append(None)
            iterations.append(it)
        
        if len(self._intervention_idx) == 1:
            idx = self._intervention_idx[0]
            if idx == -1:
                return interactions, iterations
            else:
                return [interactions[idx]], [iterations[idx]]
        else:
            final_interactions, final_iterations = [], []
            for i in self._intervention_idx:
                final_interactions.append(interactions[i])
                final_iterations.append(iterations[i])
            return final_interactions, final_iterations

    def get_pibo_intervention(self):
        return {'e_0_1': CategoricalHyperparameter('e_0_1', [0, 1], weights=[1, 1000]), 
                'e_0_2': CategoricalHyperparameter('e_0_2', [0, 1], weights=[1000, 1]), 
                'e_0_3': CategoricalHyperparameter('e_0_3', [0, 1], weights=[1, 1000]), 
                'e_0_4': CategoricalHyperparameter('e_0_4', [0, 1], weights=[1000, 1]), 
                'e_0_5': CategoricalHyperparameter('e_0_5', [0, 1], weights=[1, 1000]), 
                'e_0_6': CategoricalHyperparameter('e_0_6', [0, 1], weights=[1, 1000]), 
                'e_1_2': CategoricalHyperparameter('e_1_2', [0, 1], weights=[1, 1000]),
                'e_1_3': CategoricalHyperparameter('e_1_3', [0, 1], weights=[1000, 1]), 
                'e_1_4': CategoricalHyperparameter('e_1_4', [0, 1], weights=[1000, 1]),
                'e_1_5': CategoricalHyperparameter('e_1_5', [0, 1], weights=[1000, 1]), 
                'e_1_6': CategoricalHyperparameter('e_1_6', [0, 1], weights=[1000, 1]),
                'e_2_3': CategoricalHyperparameter('e_2_3', [0, 1], weights=[1000, 1]), 
                'e_2_4': CategoricalHyperparameter('e_2_4', [0, 1], weights=[1, 1000]), 
                'e_2_5': CategoricalHyperparameter('e_2_5', [0, 1], weights=[1000, 1]), 
                'e_2_6': CategoricalHyperparameter('e_2_6', [0, 1], weights=[1000, 1]), 
                'e_3_4': CategoricalHyperparameter('e_3_4', [0, 1], weights=[1000, 1]), 
                'e_3_5': CategoricalHyperparameter('e_3_5', [0, 1], weights=[1, 1000]), 
                'e_3_6': CategoricalHyperparameter('e_3_6', [0, 1], weights=[1000, 1]), 
                'e_4_5': CategoricalHyperparameter('e_4_5', [0, 1], weights=[1, 1000]), 
                'e_4_6': CategoricalHyperparameter('e_4_6', [0, 1], weights=[1000, 1]), 
                'e_5_6': CategoricalHyperparameter('e_5_6', [0, 1], weights=[1, 1000])
                }

    def get_bopro_intervention(self):
        return {'e_0_1': { "prior": list(np.array([1, 1000]) / sum([1, 1000]))}, 
                'e_0_2': { "prior": list(np.array([1000, 1]) / sum([1000, 1]))}, 
                'e_0_3': { "prior": list(np.array([1, 1000]) / sum([1, 1000]))}, 
                'e_0_4': { "prior": list(np.array([1000, 1]) / sum([1000, 1]))}, 
                'e_0_5': { "prior": list(np.array([1, 1000]) / sum([1, 1000]))}, 
                'e_0_6': { "prior": list(np.array([1, 1000]) / sum([1, 1000]))}, 
                'e_1_2': { "prior": list(np.array([1, 1000]) / sum([1, 1000]))},
                'e_1_3': { "prior": list(np.array([1000, 1]) / sum([1000, 1]))}, 
                'e_1_4': { "prior": list(np.array([1000, 1]) / sum([1000, 1]))},
                'e_1_5': { "prior": list(np.array([1000, 1]) / sum([1000, 1]))}, 
                'e_1_6': { "prior": list(np.array([1000, 1]) / sum([1000, 1]))},
                'e_2_3': { "prior": list(np.array([1000, 1]) / sum([1000, 1]))}, 
                'e_2_4': { "prior": list(np.array([1, 1000]) / sum([1, 1000]))}, 
                'e_2_5': { "prior": list(np.array([1000, 1]) / sum([1000, 1]))}, 
                'e_2_6': { "prior": list(np.array([1000, 1]) / sum([1000, 1]))}, 
                'e_3_4': { "prior": list(np.array([1000, 1]) / sum([1000, 1]))}, 
                'e_3_5': { "prior": list(np.array([1, 1000]) / sum([1, 1000]))}, 
                'e_3_6': { "prior": list(np.array([1000, 1]) / sum([1000, 1]))}, 
                'e_4_5': { "prior": list(np.array([1, 1000]) / sum([1, 1000]))}, 
                'e_4_6': { "prior": list(np.array([1000, 1]) / sum([1000, 1]))}, 
                'e_5_6': { "prior": list(np.array([1, 1000]) / sum([1, 1000]))}
                }
    
    def setup_bopro_json(self, benchmark):
        borpo_search_space = benchmark.search_space.to_hypermapper()
        json_dict = {
            "application_name": "NAS101 Interactive",
            "optimization_objectives": ["value"],
            "design_of_experiment": {
                "number_of_samples": 3,
            },
            "optimization_iterations": 2000,
            "optimization_method": "prior_guided_optimization",
            "number_of_cpus": 16,
            "models": {
                "model": "random_forest"
            },
            "input_parameters": borpo_search_space
        }
        if not os.path.exists('./bopro_experiments/'):
            os.mkdir('./bopro_experiments')
        self._bopro_file_name =  './bopro_experiments/nas101_interactive.json'
        with open(self._bopro_file_name, 'w+') as f:
            json.dump(json_dict, f)
