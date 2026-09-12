import re


class BatchID():
    """
    Class facilitating numbering and deriving numbering of batches,
    and checking their completeness
    """

    PATTERN: re.Pattern = re.compile(r"^(\d+)of(\d+)$")
    """
    General pattern used for batches.
    Here eg: '01of20'
    """

    @classmethod
    def generate_batch_ids(cls, number_of_batches: int) -> set[str]:
        """
        Generates a set of batch ids following the pattern of this class.
        """
        if number_of_batches <= 0:
            return set()

        width = len(str(number_of_batches))
        return {
            f"{i:0{width}d}of{number_of_batches}"
            for i in range(1, number_of_batches + 1)
        }

    @classmethod
    def is_valid(cls, batch_id: str) -> bool:
        """
        Checks if the given batch_id follows the right pattern.
        """
        return cls.PATTERN.match(batch_id) is not None

    @classmethod
    def _parse(cls, batch_id: str) -> tuple[int, int] | None:
        """
        Parses a batch_id into (part_num, part_total). Returns None if malformed.
        """
        match = cls.PATTERN.match(batch_id)
        if not match:
            return None
        return int(match.group(1)), int(match.group(2))
    
    @classmethod
    def validate_set(cls, batch_ids: set[str]) -> None:
        """
        Checks if the given set of batch ids is valid and raises a value error if not.
        Raises a ValueError
            (1) if one of the batches is mallformed
            (2) if the number of total batches indicated differs between batches
            (3) if the set of batches is incomplete
        """
        if not batch_ids:
            return False

        parts: set[int] = set()
        total: int | None = None

        for batch_id in batch_ids:
            parsed = cls._parse(batch_id)
            if parsed is None:
                raise ValueError(f"One of the batch_ids ({batch_id}) is mallformed.")

            part_num, part_total = parsed

            if total is None:
                total = part_total
            elif part_total != total:
                raise ValueError(f"The number of total batches indicated by the batch ids differs between batches.")

            parts.add(part_num)

        if len(parts) != total and parts == set(range(1, total + 1)):
            raise ValueError(f"the given set of batch ids is not complete: {batch_ids}.")

