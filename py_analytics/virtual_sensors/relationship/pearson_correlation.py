from scipy.stats import pearsonr

from .relationship_measure import RelationshipMeasure

class PearsonCorrelation(RelationshipMeasure):
    """
    Pearson Correlation Coefficient (PCC) is a measure of the linear correlation between two variables.
    It ranges from -1 to 1, where:
        1 indicates a perfect positive linear relationship,
        -1 indicates a perfect negative linear relationship,
        0 indicates no linear relationship.
    """

    def compute(self, x, y):
        """
        Compute the Pearson correlation coefficient between two variables.

        Parameters:
            x (array-like): First variable.
            y (array-like): Second variable.

        Returns:
            float: Pearson correlation coefficient.
        """
        correlation_coefficient, _ = pearsonr(x, y)
        return correlation_coefficient