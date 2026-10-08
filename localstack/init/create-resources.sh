#!/bin/bash
awslocal sqs create-queue --queue-name import-jobs-dlq --region eu-west-1
awslocal sqs create-queue --queue-name import-jobs --region eu-west-1 \
  --attributes '{"RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:eu-west-1:000000000000:import-jobs-dlq\",\"maxReceiveCount\":\"3\"}"}'