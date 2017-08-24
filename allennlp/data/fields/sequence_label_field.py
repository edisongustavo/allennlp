from typing import Dict, List, Optional, Union  # pylint: disable=unused-import
import logging

from overrides import overrides
import numpy

from allennlp.common.checks import ConfigurationError
from allennlp.common.util import pad_sequence_to_length
from allennlp.data.fields.field import Field
from allennlp.data.fields.sequence_field import SequenceField
from allennlp.data.vocabulary import Vocabulary

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class SequenceLabelField(Field[numpy.ndarray]):
    """
    A ``SequenceLabelField`` assigns a categorical label to each element in a :class:`SequenceField`.
    Because it's a labeling of some other field, we take that field as input here, and we use it to
    determine our padding and other things.

    This field will get converted into a list of integer class ids, representing the correct class
    for each element in the sequence.

    Parameters
    ----------
    labels : ``Union[List[str], List[int]]``
        A sequence of categorical labels, encoded as strings or integers.  These could be POS tags like [NN,
        JJ, ...], BIO tags like [B-PERS, I-PERS, O, O, ...], or any other categorical tag sequence. If the
        labels are encoded as integers, they will not be indexed using a vocab.
    sequence_field : ``SequenceField``
        A field containing the sequence that this ``SequenceLabelField`` is labeling.  Most often, this is a
        ``TextField``, for tagging individual tokens in a sentence.
    label_namespace : ``str``, optional (default='labels')
        The namespace to use for converting tag strings into integers.  We convert tag strings to
        integers for you, and this parameter tells the ``Vocabulary`` object which mapping from
        strings to integers to use (so that "O" as a tag doesn't get the same id as "O" as a word).
    """
    def __init__(self,
                 labels: Union[List[str], List[int]],
                 sequence_field: SequenceField,
                 label_namespace: str = 'labels') -> None:
        self._labels = labels
        self._sequence_field = sequence_field
        self._label_namespace = label_namespace
        self._indexed_labels = None

        if not (self._label_namespace.endswith("tags") or self._label_namespace.endswith("labels")):
            logger.warning("Your sequence label namespace was '%s'. We recommend you use a namespace "
                           "ending with 'tags' or 'labels', so we don't add UNK and PAD tokens by "
                           "default to your vocabulary.  See documentation for "
                           "`non_padded_namespaces` parameter in Vocabulary.", self._label_namespace)

        if len(labels) != sequence_field.sequence_length():
            raise ConfigurationError("Label length and sequence length "
                                     "don't match: %d and %d" % (len(labels), sequence_field.sequence_length()))

        if all([isinstance(x, int) for x in labels]):
            self._indexed_labels = labels

    @overrides
    def count_vocab_items(self, counter: Dict[str, Dict[str, int]]):
        if self._indexed_labels is None:
            for label in self._labels:
                counter[self._label_namespace][label] += 1  # type: ignore

    @overrides
    def index(self, vocab: Vocabulary):
        if self._indexed_labels is None:
            self._indexed_labels = [vocab.get_token_index(label, self._label_namespace)  # type: ignore
                                    for label in self._labels]

    @overrides
    def get_padding_lengths(self) -> Dict[str, int]:
        return {'num_tokens': self._sequence_field.sequence_length()}

    @overrides
    def as_array(self, padding_lengths: Dict[str, int]) -> numpy.ndarray:
        desired_num_tokens = padding_lengths['num_tokens']
        padded_tags = pad_sequence_to_length(self._indexed_labels, desired_num_tokens)
        return numpy.asarray(padded_tags)

    @overrides
    def empty_field(self):  # pylint: disable=no-self-use
        # pylint: disable=protected-access
        sequence_label_field = SequenceLabelField([], None)
        sequence_label_field._indexed_labels = []
        return sequence_label_field

    def labels(self):
        return self._labels