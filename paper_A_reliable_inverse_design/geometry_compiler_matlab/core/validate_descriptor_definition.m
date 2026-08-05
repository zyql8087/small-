function [profiles, profileHashes] = validate_descriptor_definition( ...
        definition, configDescriptorNames, errorId)
%VALIDATE_DESCRIPTOR_DEFINITION Validate the immutable M04 dual profile JSON.

    require_scalar_struct(definition, 'Descriptor definition root', errorId);
    require_exact_fields(definition, {'schema_version', 'descriptor_contract', ...
        'validation_status', 'descriptor_order', 'source_of_record', 'profiles'}, ...
        'Descriptor definition root', errorId);

    schemaVersion = validate_text_scalar(definition.schema_version, ...
        'Descriptor definition schema_version', errorId);
    if ~strcmp(schemaVersion, '2.0')
        throw(MException(errorId, ...
            'Descriptor definition schema_version "%s" must equal "2.0"', ...
            schemaVersion));
    end
    descriptorContract = validate_text_scalar(definition.descriptor_contract, ...
        'Descriptor definition descriptor_contract', errorId);
    if ~strcmp(descriptorContract, 'm04-dual-profile')
        throw(MException(errorId, ...
            'Descriptor definition descriptor_contract must equal "m04-dual-profile"'));
    end
    validationStatus = validate_text_scalar(definition.validation_status, ...
        'Descriptor definition validation_status', errorId);
    if ~strcmp(validationStatus, 'active_m04_contract')
        throw(MException(errorId, ...
            'Descriptor definition validation_status must equal "active_m04_contract"'));
    end

    descriptorOrder = normalize_text_sequence(definition.descriptor_order, ...
        'Descriptor definition descriptor_order', errorId);
    if ~isequal(descriptorOrder, configDescriptorNames)
        throw(MException(errorId, ...
            'Descriptor definition order [%s] does not match config order [%s]', ...
            strjoin(descriptorOrder, ', '), strjoin(configDescriptorNames, ', ')));
    end

    validate_source_of_record(definition.source_of_record, errorId);
    profiles = normalize_profiles(definition.profiles, errorId);
    expectedNames = {'legacy_small', 'physical_m04'};
    actualNames = cell(1, numel(profiles));
    for profileIndex = 1:numel(profiles)
        actualNames{profileIndex} = validate_profile(profiles(profileIndex), ...
            configDescriptorNames, errorId);
    end
    if ~isequal(actualNames, expectedNames)
        throw(MException(errorId, ...
            'Descriptor profile order [%s] must equal [%s]', ...
            strjoin(actualNames, ', '), strjoin(expectedNames, ', ')));
    end

    profileHashes = struct();
    for profileIndex = 1:numel(profiles)
        profileName = actualNames{profileIndex};
        profileHashes.(profileName) = sha256_text( ...
            canonical_profile_text(profiles(profileIndex), configDescriptorNames));
    end
end

function require_scalar_struct(value, label, errorId)
    if ~isstruct(value) || ~isscalar(value)
        throw(MException(errorId, '%s must be a scalar JSON object', label));
    end
end

function require_exact_fields(value, expectedFields, label, errorId)
    require_scalar_struct(value, label, errorId);
    actualFields = sort(fieldnames(value))';
    expectedFields = sort(expectedFields);
    if ~isequal(actualFields, expectedFields)
        throw(MException(errorId, '%s fields must be {%s}, got {%s}', ...
            label, strjoin(expectedFields, ', '), strjoin(actualFields, ', ')));
    end
end

function values = normalize_text_sequence(value, label, errorId)
    if ischar(value)
        values = {validate_text_scalar(value, label, errorId)};
        return;
    end
    if isstring(value)
        if ~isvector(value)
            throw(MException(errorId, '%s must be a text vector', label));
        end
        rawValues = num2cell(value(:)');
    elseif iscell(value)
        rawValues = value(:)';
    else
        throw(MException(errorId, '%s must be a text array', label));
    end
    values = cell(1, numel(rawValues));
    for index = 1:numel(rawValues)
        values{index} = validate_text_scalar(rawValues{index}, ...
            sprintf('%s entry %d', label, index), errorId);
    end
end

function validate_source_of_record(source, errorId)
    require_exact_fields(source, {'repository', 'commit'}, ...
        'Descriptor definition source_of_record', errorId);
    repository = validate_text_scalar(source.repository, ...
        'Descriptor definition source_of_record.repository', errorId);
    commit = validate_text_scalar(source.commit, ...
        'Descriptor definition source_of_record.commit', errorId);
    if ~strcmp(repository, 'https://github.com/Alistairj43/TPMS-Designer')
        throw(MException(errorId, 'Descriptor source repository is not pinned'));
    end
    if ~strcmp(commit, 'a5f7d59b59f5c00e0f50c0bc3675f38f553454eb')
        throw(MException(errorId, 'Descriptor source commit is not pinned'));
    end
end

function profiles = normalize_profiles(value, errorId)
    if ~isstruct(value) || isempty(value) || ~isvector(value)
        throw(MException(errorId, ...
            'Descriptor definition profiles must be a non-empty object array'));
    end
    profiles = value(:)';
end

function profileName = validate_profile(profile, descriptorNames, errorId)
    require_exact_fields(profile, {'name', 'grid_convention', 'units', 'algorithms'}, ...
        'Descriptor profile', errorId);
    profileName = validate_text_scalar(profile.name, ...
        'Descriptor profile name', errorId);
    expected = expected_profile(profileName, descriptorNames, errorId);
    gridConvention = validate_text_scalar(profile.grid_convention, ...
        sprintf('Descriptor profile %s grid_convention', profileName), errorId);
    if ~strcmp(gridConvention, expected.grid_convention)
        throw(MException(errorId, ...
            'Descriptor profile %s grid_convention must equal "%s"', ...
            profileName, expected.grid_convention));
    end
    validate_named_text_map(profile.units, descriptorNames, expected.units, ...
        sprintf('Descriptor profile %s units', profileName), errorId);
    validate_named_text_map(profile.algorithms, descriptorNames, ...
        expected.algorithms, sprintf('Descriptor profile %s algorithms', ...
        profileName), errorId);
end

function expected = expected_profile(profileName, descriptorNames, errorId)
    expected = struct();
    expected.units = struct();
    expected.algorithms = struct();
    switch profileName
        case 'legacy_small'
            expected.grid_convention = 'endpoint_grid';
            expected.units.relativeVolume = 'dimensionless';
            expected.units.relativeArea = 'dimensionless';
            expected.units.thickness = 'mm';
            expected.units.poreDiameter = 'mm';
            expected.units.areaMean = 'mm2';
            expected.algorithms.relativeVolume = 'drop_final_plane_occupancy';
            expected.algorithms.relativeArea = 'surface_area_over_bbox_surface_area';
            expected.algorithms.thickness = ...
                'periodic_maximum_solid_inscribed_diameter';
            expected.algorithms.poreDiameter = ...
                'periodic_maximum_void_inscribed_diameter';
            expected.algorithms.areaMean = 'mean_solid_z_slice_area';
        case 'physical_m04'
            expected.grid_convention = 'm03_cell_centered_interior';
            expected.units.relativeVolume = 'dimensionless';
            expected.units.relativeArea = 'mm^-1';
            expected.units.thickness = 'mm';
            expected.units.poreDiameter = 'mm';
            expected.units.areaMean = 'mm2';
            expected.algorithms.relativeVolume = 'interior_solid_fraction';
            expected.algorithms.relativeArea = ...
                'closed_surface_area_over_bbox_volume';
            expected.algorithms.thickness = 'median_skeleton_local_thickness';
            expected.algorithms.poreDiameter = ...
                'largest_finite_void_component_inscribed_diameter';
            expected.algorithms.areaMean = ...
                'mean_largest_void_region_over_26_z_slices';
        otherwise
            throw(MException(errorId, ...
                'Descriptor profile name "%s" is not supported', profileName));
    end
    if ~isequal(sort(fieldnames(expected.units))', sort(descriptorNames)) || ...
            ~isequal(sort(fieldnames(expected.algorithms))', sort(descriptorNames))
        throw(MException(errorId, 'Internal descriptor profile contract mismatch'));
    end
end

function validate_named_text_map(value, names, expected, label, errorId)
    require_exact_fields(value, names, label, errorId);
    for index = 1:numel(names)
        name = names{index};
        actualValue = validate_text_scalar(value.(name), ...
            sprintf('%s.%s', label, name), errorId);
        if ~strcmp(actualValue, expected.(name))
            throw(MException(errorId, '%s.%s must equal "%s"', ...
                label, name, expected.(name)));
        end
    end
end

function text = canonical_profile_text(profile, descriptorNames)
    values = cell(1, 2 + 2 * numel(descriptorNames));
    values{1} = sprintf('profile=%s\n', profile.name);
    values{2} = sprintf('grid_convention=%s\n', profile.grid_convention);
    writeIndex = 3;
    for index = 1:numel(descriptorNames)
        name = descriptorNames{index};
        values{writeIndex} = sprintf('unit.%s=%s\n', name, ...
            profile.units.(name));
        values{writeIndex + 1} = sprintf('algorithm.%s=%s\n', name, ...
            profile.algorithms.(name));
        writeIndex = writeIndex + 2;
    end
    text = [values{:}];
end
