"""
Answer upload for agent QA.

Posts answer JSON directly to the API endpoint.
"""

import json

import requests
from qa.ai_response_parser import AIResponseParser
from questions.question_type import QuestionTypeName


def upload_answer(
    api_endpoint: str,
    api_key: str,
    qa_job_id: int,
    matrix_cell_id: int,
    question_type_id: int,
    answer_json: str,
) -> None:
    """
    Upload answer JSON to API endpoint.

    Args:
        api_endpoint: API endpoint base URL
        api_key: Service account API key
        qa_job_id: QA job ID
        matrix_cell_id: Matrix cell ID
        question_type_id: Question type ID
        answer_json: JSON string containing answer data

    Raises:
        Exception: If upload fails
    """
    # Convert question_type_id to enum
    question_type = QuestionTypeName.from_id(question_type_id)

    # Use AIResponseParser to transform JSON (handles order → citation_number, etc.)
    answer_set = AIResponseParser.parse_response(answer_json, question_type)

    # Convert answer_set to API payload format
    # answer_set.answers contains properly formatted AnswerData objects
    answers_list = []
    for answer in answer_set.answers:
        # Convert domain model to dict for JSON serialization
        answer_dict = answer.model_dump()
        answers_list.append(answer_dict)

    # Build payload matching API schema
    payload = {
        "matrix_cell_id": matrix_cell_id,
        "question_type_id": question_type_id,
        "answer_found": answer_set.answer_found,
        "answers": answers_list,
    }

    # Build URL
    url = f"{api_endpoint}/api/v1/qa-jobs/{qa_job_id}/answer"

    print(f"Uploading answer to {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    # POST to API
    response = requests.post(
        url,
        json=payload,
        headers={
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        },
        timeout=30,
    )

    if response.status_code not in [200, 201]:
        raise Exception(
            f"Failed to upload answer: {response.status_code} - {response.text}"
        )

    print(f"Answer uploaded successfully: {response.json()}")
