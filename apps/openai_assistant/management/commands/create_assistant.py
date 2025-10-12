import json
import sys
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from apps.openai_assistant.models import Assistant, Tool
from apps.openai_assistant.services import OpenAIService

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a new OpenAI Assistant'

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True, help='Name of the assistant')
        parser.add_argument('--description', default='', help='Description of the assistant')
        parser.add_argument('--instructions', required=True, help='Instructions for the assistant')
        parser.add_argument('--model', default='gpt-4o', help='Model to use (default: gpt-4o)')
        parser.add_argument('--user', help='Username of the user who creates the assistant')
        parser.add_argument('--tools', help='JSON string or file path containing tools configuration')
        parser.add_argument('--code-interpreter', action='store_true', help='Add code interpreter tool')
        parser.add_argument('--retrieval', action='store_true', help='Add retrieval tool')

    def handle(self, *args, **options):
        try:
            # Get or create user
            user = None
            if options['user']:
                try:
                    user = User.objects.get(username=options['user'])
                except User.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"User {options['user']} not found. Assistant will be created without a user."))
            
            # Create assistant
            assistant = Assistant.objects.create(
                name=options['name'],
                description=options['description'],
                instructions=options['instructions'],
                model=options['model'],
                created_by=user
            )
            
            # Add tools
            tools_data = []
            
            # Add code interpreter if requested
            if options['code_interpreter']:
                Tool.objects.create(
                    assistant=assistant,
                    name='code_interpreter',
                    type='code_interpreter',
                    description='Execute code'
                )
                self.stdout.write(self.style.SUCCESS('Added code interpreter tool'))
            
            # Add retrieval if requested
            if options['retrieval']:
                Tool.objects.create(
                    assistant=assistant,
                    name='retrieval',
                    type='retrieval',
                    description='Retrieve information from files'
                )
                self.stdout.write(self.style.SUCCESS('Added retrieval tool'))
            
            # Add function tools if provided
            if options['tools']:
                tools_input = options['tools']
                
                # Check if it's a file path
                if tools_input.endswith('.json'):
                    try:
                        with open(tools_input, 'r') as f:
                            tools_data = json.load(f)
                    except Exception as e:
                        print(e)
                        raise CommandError(f"Error reading tools file: {str(e)}")
                else:
                    # Try to parse as JSON string
                    try:
                        tools_data = json.loads(tools_input)
                    except json.JSONDecodeError:
                        raise CommandError("Invalid JSON format for tools")
                
                # Create tools
                for tool_data in tools_data:
                    Tool.objects.create(
                        assistant=assistant,
                        name=tool_data.get('name'),
                        type='function',
                        description=tool_data.get('description', ''),
                        parameters=tool_data.get('parameters', {})
                    )
                
                self.stdout.write(self.style.SUCCESS(f'Added {len(tools_data)} function tools'))
            
            # Create in OpenAI
            openai_service = OpenAIService()
            openai_id = openai_service.create_assistant(assistant)
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created assistant "{assistant.name}" with ID: {assistant.id}'))
            self.stdout.write(self.style.SUCCESS(f'OpenAI Assistant ID: {openai_id}'))
            
        except Exception as e:
            print(e)
            raise CommandError(f"Error creating assistant: {str(e)}")