import asyncio
from typing import Dict, List

import httpx
from loguru import logger


async def fetch_single_protein(
    client: httpx.AsyncClient, uniprot_id: str
) -> tuple[str, str | None]:
    """Fetch a single protein sequence from Uniprot."""
    url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.fasta"
    try:
        await asyncio.sleep(0.1)  # Rate limiting
        response = await client.get(url)
        if response.status_code != 200:
            logger.error(f"Failed to fetch protein sequence for {uniprot_id}")
            return uniprot_id, None
        return uniprot_id, extract_protein_sequence(response.text)
    except Exception as e:
        logger.error(f"Error fetching {uniprot_id}: {str(e)}")
        return uniprot_id, None


async def fetch_uniprot_protein_fasta(uniprot_ids: List[str]) -> Dict[str, str]:
    """
    Fetch protein sequences from Uniprot for a list of Uniprot IDs concurrently.
    Returns a dictionary mapping Uniprot IDs to their sequences.
    Failed fetches are excluded from the result.
    """
    async with httpx.AsyncClient() as client:
        tasks = [fetch_single_protein(client, uniprot_id) for uniprot_id in uniprot_ids]
        results = await asyncio.gather(*tasks)
        return {id_: seq for id_, seq in results if seq is not None}


def extract_protein_sequence(fasta_string: str) -> str:
    """Extract the protein sequence from a FASTA string, removing header and newlines."""
    lines = fasta_string.split("\n")
    sequence_lines = lines[1:]  # Skip the header line
    return "".join(sequence_lines).strip()


async def main():
    return await fetch_uniprot_protein_fasta(["P00761", "P00762", "P12345"])


if __name__ == "__main__":
    print(asyncio.run(main()))
