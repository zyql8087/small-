function projected = project_method_constraints(method, parameters, config)
%PROJECT_METHOD_CONSTRAINTS Apply the frozen M1/M2/M3 parameter contract.
%   PROJECTED = PROJECT_METHOD_CONSTRAINTS(METHOD, PARAMETERS, CONFIG)
%   validates the four raw controls, applies the documented M2 orthogonal
%   projection, and enforces method-specific bounds from validated CONFIG.

    INVALID_REQUEST = 'MATLABGyroid:InvalidRequest';
    METHOD_CONSTRAINT = 'MATLABGyroid:MethodConstraint';
    OUT_OF_BOUNDS = 'MATLABGyroid:OutOfBounds';

    if nargin ~= 3
        throw(MException(INVALID_REQUEST, ...
            'project_method_constraints requires method, parameters, and config'));
    end

    method = validate_text_scalar(method, 'method', INVALID_REQUEST);
    allowedMethods = {'M1', 'M2', 'M3'};
    if ~ismember(method, allowedMethods)
        throw(MException(INVALID_REQUEST, ...
            'method must be one of {M1, M2, M3}, got "%s"', method));
    end

    if ~isstruct(parameters) || ~isscalar(parameters)
        throw(MException(INVALID_REQUEST, ...
            'parameters must be a scalar struct'));
    end
    parameterNames = {'c0', 'c1', 'c2', 'w'};
    actualNames = sort(fieldnames(parameters))';
    expectedNames = sort(parameterNames);
    if ~isequal(actualNames, expectedNames)
        throw(MException(INVALID_REQUEST, ...
            'parameters must have fields {c0, c1, c2, w}, got {%s}', ...
            strjoin(actualNames, ', ')));
    end
    for parameterIndex = 1:numel(parameterNames)
        parameterName = parameterNames{parameterIndex};
        value = parameters.(parameterName);
        if ~isnumeric(value) || ~isscalar(value) || ~isreal(value) || ...
                ~isfinite(value)
            throw(MException(INVALID_REQUEST, ...
                'parameters.%s must be a finite real numeric scalar', ...
                parameterName));
        end
    end

    if ~isstruct(config) || ~isscalar(config) || ...
            ~isfield(config, 'method_bounds') || ...
            ~isfield(config.method_bounds, method)
        throw(MException(INVALID_REQUEST, ...
            'config must be a validated compiler configuration containing %s', ...
            method));
    end

    projected = struct();
    projected.method = method;
    projected.c0 = double(parameters.c0);
    projected.c1 = double(parameters.c1);
    projected.c2 = double(parameters.c2);
    projected.w = double(parameters.w);
    projected.c_projected = [];
    projected.projection_applied = false;
    projected.projection_l2 = 0;
    projected.raw_parameters = parameters;

    switch method
        case 'M1'
            fixedW = config.method_bounds.M1.fixed_variables.w;
            if projected.w ~= fixedW
                throw(MException(METHOD_CONSTRAINT, ...
                    'M1 requires w=%g, got %g', fixedW, projected.w));
            end
            activeNames = {'c0', 'c1', 'c2'};
        case 'M2'
            rawThresholds = [projected.c0, projected.c1, projected.c2];
            if all(rawThresholds == rawThresholds(1))
                cProjected = rawThresholds(1);
            else
                cProjected = mean(rawThresholds);
            end
            projected.c0 = cProjected;
            projected.c1 = cProjected;
            projected.c2 = cProjected;
            projected.c_projected = cProjected;
            projected.projection_l2 = norm(rawThresholds - cProjected);
            projected.projection_applied = projected.projection_l2 > 0;
            activeNames = {'c_projected', 'w'};
        case 'M3'
            activeNames = {'c0', 'c1', 'c2', 'w'};
    end

    bounds = config.method_bounds.(method).bounds;
    for activeIndex = 1:numel(activeNames)
        activeName = activeNames{activeIndex};
        validate_bound(projected.(activeName), bounds.(activeName), ...
            method, activeName, OUT_OF_BOUNDS);
    end
end

function validate_bound(value, bound, method, variableName, errorId)
    below = value < bound.lower || ...
        (value == bound.lower && ~bound.lower_inclusive);
    above = value > bound.upper || ...
        (value == bound.upper && ~bound.upper_inclusive);
    if below || above
        lowerBracket = '(';
        if bound.lower_inclusive
            lowerBracket = '[';
        end
        upperBracket = ')';
        if bound.upper_inclusive
            upperBracket = ']';
        end
        throw(MException(errorId, ...
            '%s.%s=%g is outside %s%g, %g%s', ...
            method, variableName, value, lowerBracket, bound.lower, ...
            bound.upper, upperBracket));
    end
end
