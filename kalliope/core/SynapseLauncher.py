import logging

from kalliope.core.ConfigurationManager import BrainLoader
from kalliope.core.Cortex import Cortex
from kalliope.core.HookManager import HookManager
from kalliope.core.Lifo.LifoManager import LifoManager
from kalliope.core.Models.MatchedSynapse import MatchedSynapse
from kalliope.core.OrderAnalyser import OrderAnalyser


logging.basicConfig()
logger = logging.getLogger("kalliope")


class SynapseNameNotFound(Exception):
    """
    The Synapse has not been found

    .. seealso: Synapse
    """
    pass


class SynapseLauncher(object):

    @classmethod
    def start_synapse_by_list_name(cls, list_name, brain=None, overriding_parameter_dict=None, new_lifo=False):
        """
        Start synapses by their name
        :param list_name: List of name of the synapse to launch
        :param brain: Brain instance
        :param overriding_parameter_dict: parameter to pass to neurons
        :param new_lifo: If True, ask the LifoManager to return a new lifo and not the singleton
        """
        logger.debug("[SynapseLauncher] start_synapse_by_list_name called with synapse list: %s " % list_name)

        if list_name:
            if brain is None:
                brain = BrainLoader().brain

            if overriding_parameter_dict:
                # this dict is used by signals to pass parameter to neuron,
                # save in temp memory in case the user want to save in kalliope memory
                Cortex.add_parameters_from_order(overriding_parameter_dict)

            # get all synapse object
            list_synapse_object_to_start = list()
            for name in list_name:
                synapse_to_start = brain.get_synapse_by_name(synapse_name=name)
                if not synapse_to_start:
                    raise SynapseNameNotFound("[SynapseLauncher] The synapse name \"%s\" does not exist "
                                              "in the brain file" % name)
                if synapse_to_start.enabled:
                    list_synapse_object_to_start.append(synapse_to_start)
                else: logger.debug("[SynapseLauncher] Synapse not activated: %s " % synapse_to_start)

            # run the LIFO with all synapse
            if new_lifo:
                lifo_buffer = LifoManager.get_new_lifo()
            else:
                lifo_buffer = LifoManager.get_singleton_lifo()
            list_synapse_to_process = list()
            for synapse in list_synapse_object_to_start:
                if synapse is not None:
                    new_matching_synapse = MatchedSynapse(matched_synapse=synapse,
                                                          matched_order=None,
                                                          user_order=None,
                                                          overriding_parameter=overriding_parameter_dict)
                    list_synapse_to_process.append(new_matching_synapse)

            lifo_buffer.add_synapse_list_to_lifo(list_synapse_to_process)
            return lifo_buffer.execute(is_api_call=True)
        return None

    @classmethod
    def run_matching_synapse_from_order(cls, order_to_process, brain, settings, is_api_call=False):
        """
        
        :param order_to_process: the spoken order sent by the user
        :param brain: Brain object
        :param settings: Settings object
        :param is_api_call: if True, the current call come from the API. This info must be known by launched Neuron
        :return: list of matched synapse
        """

        # get our singleton LIFO
        lifo_buffer = LifoManager.get_singleton_lifo()

        # if the LIFO is not empty, so, the current order is passed to the current processing synapse as an answer
        if len(lifo_buffer.lifo_list) > 0:
            # the LIFO is not empty, this is an answer to a previous call
            return lifo_buffer.execute(answer=order_to_process, is_api_call=is_api_call)

        else:  # the LIFO is empty, this is a new call
            # get a list of matched synapse from the order
            list_synapse_to_process = OrderAnalyser.get_matching_synapse(order=order_to_process, brain=brain)

            if not list_synapse_to_process:  # the order analyser returned us an empty list
                return HookManager.on_order_not_found()
            else:
                HookManager.on_order_found()

            lifo_buffer.add_synapse_list_to_lifo(list_synapse_to_process)
            lifo_buffer.api_response.user_order = order_to_process

            execdata = lifo_buffer.execute(is_api_call=is_api_call)
            HookManager.on_processed_synapses()
            return execdata
