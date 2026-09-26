from scipy.stats import spearmanr

from .relationship_measure import RelationshipMeasure

class SpearmanCorrelation(RelationshipMeasure):
    """
    Spearman Rank Correlation Coefficient (SRC) is a non-parametric measure of the monotonic relationship between two variables.
    It ranges from -1 to 1, where:
        1 indicates a perfect positive monotonic relationship,
        -1 indicates a perfect negative monotonic relationship,
        0 indicates no monotonic relationship.
    """

    def compute(self, x, y):
        """
        Compute the Spearman rank correlation coefficient between two variables.

        Parameters:
            x (array-like): First variable.
            y (array-like): Second variable.

        Returns:
            float: Spearman rank correlation coefficient.
        """
        correlation_coefficient, _ = spearmanr(x, y)
        return correlation_coefficient