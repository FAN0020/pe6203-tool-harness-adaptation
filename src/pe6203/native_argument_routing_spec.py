"""Frozen tool-only contract data from native-argument-routing-updater-v1.

No task content, benchmark answer, trajectory or score is embedded.
Spec SHA256: dfffa7ca256ea010eb69441115b8b7519cd19b23a2401accf5d9cf88300fd325
"""

SERVER = '@magicuidesign/mcp'

TRIGGERS = ('@magicuidesign/mcp::getComponentDetails',
 '@magicuidesign/mcp::getComponentsByNames',
 '@magicuidesign/mcp::searchComponents')

FINGERPRINT_FIELDS = ('name', 'parameters', 'description', 'output_schema', 'routing')

ANNOTATIONS = {'@magicuidesign/mcp::getComponentDetails': {'before': 'Retrieves comprehensive implementation '
                                                       'details for a single Magic UI '
                                                       'component by name, including full '
                                                       'source code, installation '
                                                       'instructions, and all associated '
                                                       'examples. Use this when you already '
                                                       'know one component name (e.g., from '
                                                       'searchComponents or getComponentIndex '
                                                       'results) and need its complete '
                                                       'implementation. If you already know '
                                                       'several component names, use '
                                                       'getComponentsByNames instead.',
                                             'after': 'This native binding exposes an empty '
                                                      'input schema and loses componentName. A '
                                                      'real name still produces Component '
                                                      '"undefined" not found (isError=true); '
                                                      'another spelling cannot restore the '
                                                      'missing argument binding. Obtain '
                                                      'implementation code from an appropriate '
                                                      'original zero-argument category tool, '
                                                      'such as getTextAnimations or '
                                                      'getSpecialEffects, and select a '
                                                      'component actually returned. '
                                                      'getComponentIndex supplies '
                                                      'category/name metadata, not '
                                                      'implementation code.',
                                             'native_contract_sha256': '1e46d6b0d80a9ee8869ec020c58cd420ab35d4b5ac80e63dc63560c37a56c0da'},
 '@magicuidesign/mcp::getComponentsByNames': {'before': 'Retrieves comprehensive '
                                                        'implementation details for multiple '
                                                        'known Magic UI components in a single '
                                                        'request, including full source code, '
                                                        'installation instructions, and '
                                                        'associated examples for each found '
                                                        'component. Use this after '
                                                        'getComponentIndex or searchComponents '
                                                        'when you already know a specific set '
                                                        'of component names and want a '
                                                        'targeted batch fetch without pulling '
                                                        'an entire category.',
                                              'after': 'This native binding exposes an empty '
                                                       'input schema and loses componentNames. '
                                                       'A real list still produces No valid '
                                                       'component names (isError=true); '
                                                       'changing the list cannot restore the '
                                                       'missing argument binding. Obtain '
                                                       'implementation code from an '
                                                       'appropriate original zero-argument '
                                                       'category tool, such as '
                                                       'getTextAnimations or '
                                                       'getSpecialEffects, and select '
                                                       'components actually returned. There is '
                                                       'no working exact-name batch fetch '
                                                       'through this binding.',
                                              'native_contract_sha256': '8a35ab3e95fe1541823524e7f7ed73a210791cc2e6ccf0cc3e62f271300a1ef4'},
 '@magicuidesign/mcp::searchComponents': {'before': 'Searches Magic UI components by keyword '
                                                    '(matched against name and description) '
                                                    'with an optional category filter. Returns '
                                                    'matching components with their category '
                                                    'assignments and example counts. After '
                                                    'finding relevant components, use '
                                                    'getComponentDetails to fetch a single '
                                                    "component's full implementation, "
                                                    'getComponentsByNames to fetch several '
                                                    'selected matches at once, or call the '
                                                    'appropriate category tool to retrieve '
                                                    'multiple components at once.',
                                          'after': 'This native binding exposes an empty input '
                                                   'schema and loses query/category. Its '
                                                   'successful envelope returns the broad '
                                                   'component inventory with no effective '
                                                   'keyword or category filtering. Do not '
                                                   'interpret that result as filtered matches. '
                                                   'For categorized discovery use '
                                                   'getComponentIndex, then select a relevant '
                                                   'original zero-argument category tool to '
                                                   'retrieve implementation code. The new '
                                                   'getComponentDetails and '
                                                   'getComponentsByNames bindings also lose '
                                                   'their arguments.',
                                          'native_contract_sha256': 'b93910f527881ca5d0e5396ccbe15c496937a73421e9c3d5275319cdd0c061f6'},
 '@magicuidesign/mcp::getUIComponents': {'before': 'Provides the complete raw catalog of all '
                                                   'Magic UI components without implementation '
                                                   'code or examples. For discovery, use '
                                                   'getComponentIndex (categorized overview) '
                                                   'or searchComponents (keyword/category '
                                                   'filtering). To fetch full implementation '
                                                   'details, use getComponentDetails for a '
                                                   'single component, getComponentsByNames for '
                                                   'a selected set of known components, or '
                                                   'category-specific tools for bulk '
                                                   'retrieval.',
                                         'after': 'Provides the complete raw catalog of Magic '
                                                  'UI components without implementation code '
                                                  'or examples. getComponentIndex provides a '
                                                  'categorized overview. In this version '
                                                  'searchComponents loses filtering arguments, '
                                                  'while getComponentDetails and '
                                                  'getComponentsByNames lose name arguments. '
                                                  'For implementation code use the relevant '
                                                  'original zero-argument category tool and '
                                                  'select components actually returned.',
                                         'native_contract_sha256': '799f4c45464b9b2eaea2a0fbdc28a69e8e4f4baf78c378d3f2322eecc1e816f8'},
 '@magicuidesign/mcp::getComponentIndex': {'before': 'Provides a full categorized index of '
                                                     'Magic UI components with example '
                                                     'coverage counts to help clients discover '
                                                     'components by category. Use '
                                                     'searchComponents for '
                                                     'keyword/category-filtered queries. Once '
                                                     'you identify components, call '
                                                     'getComponentDetails for a single '
                                                     'component, getComponentsByNames for a '
                                                     'hand-picked list of known components, or '
                                                     'use category-specific tools to fetch '
                                                     'multiple components at once.',
                                           'after': 'Provides a categorized index of Magic UI '
                                                    'component names with example coverage '
                                                    'counts; these entries are metadata, not '
                                                    'implementation code. In this version '
                                                    'searchComponents loses filtering '
                                                    'arguments, while getComponentDetails and '
                                                    'getComponentsByNames lose name arguments. '
                                                    'Use the relevant original zero-argument '
                                                    'category tool, such as getTextAnimations '
                                                    'or getSpecialEffects, to obtain actual '
                                                    'component implementations.',
                                           'native_contract_sha256': '77090d7b85c207752df9026836c7eb552599c1f381cdc98cf966d02dec782923'},
 '@magicuidesign/mcp::getTextAnimations': {'before': 'Provides detailed implementation data '
                                                     'for text-animate, line-shadow-text, '
                                                     'aurora-text, number-ticker, '
                                                     'animated-shiny-text, '
                                                     'animated-gradient-text, text-reveal, '
                                                     'hyper-text, word-rotate, '
                                                     'typing-animation, scroll-based-velocity, '
                                                     'flip-text, box-reveal, sparkles-text, '
                                                     'morphing-text, spinning-text components '
                                                     'in the TextAnimations category. Use '
                                                     'getComponentIndex first if you need a '
                                                     'categorized discovery overview before '
                                                     'fetching full component code and '
                                                     'examples. If you only need a selected '
                                                     'subset of known components, use '
                                                     'getComponentsByNames instead.',
                                           'after': 'Provides detailed implementation data for '
                                                    'text-animate, line-shadow-text, '
                                                    'aurora-text, number-ticker, '
                                                    'animated-shiny-text, '
                                                    'animated-gradient-text, text-reveal, '
                                                    'hyper-text, word-rotate, '
                                                    'typing-animation, scroll-based-velocity, '
                                                    'flip-text, box-reveal, sparkles-text, '
                                                    'morphing-text, spinning-text components '
                                                    'in the TextAnimations category. Use '
                                                    'getComponentIndex first if you need a '
                                                    'categorized discovery overview before '
                                                    'fetching full component code and '
                                                    'examples. This zero-argument category '
                                                    'route returns component source and '
                                                    'installation instructions; select a '
                                                    'component actually present in the '
                                                    'response. The new exact-name and batch '
                                                    'bindings lose their arguments. Component '
                                                    'source requires its stated framework '
                                                    'dependencies and is not itself a rendered '
                                                    'standalone webpage.',
                                           'native_contract_sha256': '1e77c6c19eb7da753177f1ebc5a6858e6f5016737f8a12cfe1610742988661e8'},
 '@magicuidesign/mcp::getSpecialEffects': {'before': 'Provides detailed implementation data '
                                                     'for animated-beam, border-beam, '
                                                     'shine-border, magic-card, meteors, '
                                                     'neon-gradient-card, confetti, particles, '
                                                     'cool-mode, scratch-to-reveal components '
                                                     'in the SpecialEffects category. Use '
                                                     'getComponentIndex first if you need a '
                                                     'categorized discovery overview before '
                                                     'fetching full component code and '
                                                     'examples. If you only need a selected '
                                                     'subset of known components, use '
                                                     'getComponentsByNames instead.',
                                           'after': 'Provides detailed implementation data for '
                                                    'animated-beam, border-beam, shine-border, '
                                                    'magic-card, meteors, neon-gradient-card, '
                                                    'confetti, particles, cool-mode, '
                                                    'scratch-to-reveal components in the '
                                                    'SpecialEffects category. Use '
                                                    'getComponentIndex first if you need a '
                                                    'categorized discovery overview before '
                                                    'fetching full component code and '
                                                    'examples. This zero-argument category '
                                                    'route returns component source and '
                                                    'installation instructions; select a '
                                                    'component actually present in the '
                                                    'response. The new exact-name and batch '
                                                    'bindings lose their arguments. Component '
                                                    'source requires its stated framework '
                                                    'dependencies and is not itself a rendered '
                                                    'standalone webpage.',
                                           'native_contract_sha256': '8cbaec724aaec7ca2ce93edea76eedfcf352492179f413149087c998e06c9be2'}}

FACTS = {'@magicuidesign/mcp::getComponentDetails': {'kind': 'native_argument_routing_v1',
                                             'parameter': 'componentName',
                                             'empty_input_schema': True,
                                             'is_error': True,
                                             'error': 'Component "undefined" not found'},
 '@magicuidesign/mcp::getComponentsByNames': {'kind': 'native_argument_routing_v1',
                                              'parameter': 'componentNames',
                                              'empty_input_schema': True,
                                              'is_error': True,
                                              'error': 'No valid component names'},
 '@magicuidesign/mcp::searchComponents': {'kind': 'native_argument_routing_v1',
                                          'empty_input_schema': True,
                                          'query_omitted': True,
                                          'category_null': True,
                                          'unfiltered_results': True,
                                          'is_error': False},
 '@magicuidesign/mcp::getTextAnimations': {'kind': 'native_argument_routing_v1',
                                           'zero_argument_route': True,
                                           'native_component_source_returned': True,
                                           'installation_instructions_returned': True},
 '@magicuidesign/mcp::getSpecialEffects': {'kind': 'native_argument_routing_v1',
                                           'zero_argument_route': True,
                                           'native_component_source_returned': True,
                                           'installation_instructions_returned': True}}

