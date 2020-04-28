ENV:=prod
COMMIT_HASH    := $$(git log -1 --pretty=%h)
DATE := $$(date +"%Y-%m-%d")
CTX:=.
AWS_ACCOUNT_ID:=$$(aws-vault exec ${ENV} -- aws sts get-caller-identity | jq .Account -r)


deploy: #export-deps
	# chmod -R 777 ./chalicelib
	poetry run chalice deploy --stage ${ENV} --profile ${ENV}

role:
	python make_role.py

export-deps:
	poetry export -f requirements.txt > requirements.txt --without-hashes

env-to-json:
	# pipx install json-dotenv
	python3 -c 'import json, os, dotenv;print(json.dumps(dotenv.dotenv_values(".env.production")))' | jq

ssm-update:
	@echo "Updating parameters for ${AWS_ACCOUNT_ID}/${APP_NAME} from .env.production"
	python3 -c 'import json, os, dotenv; values={k.lower():v for k,v in dotenv.dotenv_values(".env.production").items()}; print(json.dumps(values))' | jq | chamber import ${APP_NAME} -


invoke:
	chalice invoke -n check-agents --profile ${ENV} --stage ${ENV}
