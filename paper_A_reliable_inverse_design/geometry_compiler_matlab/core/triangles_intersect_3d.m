function tf = triangles_intersect_3d(first, second, tolerance)
%TRIANGLES_INTERSECT_3D Test two non-degenerate 3-D triangles.

    validate_triangle(first, 'first');
    validate_triangle(second, 'second');
    if ~isnumeric(tolerance) || ~isscalar(tolerance) || ...
            ~isreal(tolerance) || ~isfinite(tolerance) || tolerance < 0
        throw(MException('MATLABGyroid:InvalidMesh', ...
            'intersection tolerance must be a finite nonnegative scalar'));
    end
    first = double(first);
    second = double(second);
    tolerance = double(tolerance);
    normalFirst = cross(first(2, :) - first(1, :), ...
        first(3, :) - first(1, :));
    normalSecond = cross(second(2, :) - second(1, :), ...
        second(3, :) - second(1, :));
    normFirst = norm(normalFirst);
    normSecond = norm(normalSecond);
    if normFirst <= tolerance || normSecond <= tolerance
        throw(MException('MATLABGyroid:InvalidMesh', ...
            'triangle intersection input must be non-degenerate'));
    end
    normalFirst = normalFirst ./ normFirst;
    normalSecond = normalSecond ./ normSecond;
    distanceSecond = (second - first(1, :)) * normalFirst';
    distanceFirst = (first - second(1, :)) * normalSecond';
    if all(distanceSecond > tolerance) || ...
            all(distanceSecond < -tolerance) || ...
            all(distanceFirst > tolerance) || ...
            all(distanceFirst < -tolerance)
        tf = false;
        return;
    end

    parallelTolerance = max(tolerance, 64 * eps);
    if norm(cross(normalFirst, normalSecond)) <= parallelTolerance
        if max(abs(distanceSecond)) > tolerance || ...
                max(abs(distanceFirst)) > tolerance
            tf = false;
            return;
        end
        [~, droppedAxis] = max(abs(normalFirst));
        keptAxes = setdiff(1:3, droppedAxis, 'stable');
        tf = coplanar_overlap_2d( ...
            first(:, keptAxes), second(:, keptAxes), tolerance);
        return;
    end

    edges = [1 2;2 3;3 1];
    tf = false;
    for edgeIndex = 1:3
        if segment_hits_triangle(first(edges(edgeIndex, 1), :), ...
                first(edges(edgeIndex, 2), :), second, tolerance) || ...
                segment_hits_triangle(second(edges(edgeIndex, 1), :), ...
                second(edges(edgeIndex, 2), :), first, tolerance)
            tf = true;
            return;
        end
    end
end

function validate_triangle(value, label)
    if ~isnumeric(value) || ~isequal(size(value), [3, 3]) || ...
            ~isreal(value) || any(~isfinite(value(:)))
        throw(MException('MATLABGyroid:InvalidMesh', ...
            '%s triangle must be a finite real 3-by-3 array', label));
    end
end

function tf = segment_hits_triangle(startPoint, endPoint, triangle, tolerance)
    direction = endPoint - startPoint;
    edgeOne = triangle(2, :) - triangle(1, :);
    edgeTwo = triangle(3, :) - triangle(1, :);
    pVector = cross(direction, edgeTwo);
    determinant = dot(edgeOne, pVector);
    determinantTolerance = tolerance * max(1, ...
        norm(direction) * norm(edgeOne) * norm(edgeTwo));
    if abs(determinant) <= determinantTolerance
        tf = false;
        return;
    end
    inverseDeterminant = 1 / determinant;
    tVector = startPoint - triangle(1, :);
    u = dot(tVector, pVector) * inverseDeterminant;
    qVector = cross(tVector, edgeOne);
    v = dot(direction, qVector) * inverseDeterminant;
    segmentParameter = dot(edgeTwo, qVector) * inverseDeterminant;
    tf = u >= -tolerance && v >= -tolerance && ...
        u + v <= 1 + tolerance && ...
        segmentParameter >= -tolerance && ...
        segmentParameter <= 1 + tolerance;
end

function tf = coplanar_overlap_2d(first, second, tolerance)
    edges = [1 2;2 3;3 1];
    for firstEdge = 1:3
        for secondEdge = 1:3
            if segments_intersect_2d( ...
                    first(edges(firstEdge, 1), :), ...
                    first(edges(firstEdge, 2), :), ...
                    second(edges(secondEdge, 1), :), ...
                    second(edges(secondEdge, 2), :), tolerance)
                tf = true;
                return;
            end
        end
    end
    tf = point_in_triangle_2d(first(1, :), second, tolerance) || ...
        point_in_triangle_2d(second(1, :), first, tolerance);
end

function tf = segments_intersect_2d(a, b, c, d, tolerance)
    o1 = orient2d(a, b, c);
    o2 = orient2d(a, b, d);
    o3 = orient2d(c, d, a);
    o4 = orient2d(c, d, b);
    if ((o1 > tolerance && o2 < -tolerance) || ...
            (o1 < -tolerance && o2 > tolerance)) && ...
            ((o3 > tolerance && o4 < -tolerance) || ...
            (o3 < -tolerance && o4 > tolerance))
        tf = true;
        return;
    end
    tf = (abs(o1) <= tolerance && point_on_segment(c, a, b, tolerance)) || ...
        (abs(o2) <= tolerance && point_on_segment(d, a, b, tolerance)) || ...
        (abs(o3) <= tolerance && point_on_segment(a, c, d, tolerance)) || ...
        (abs(o4) <= tolerance && point_on_segment(b, c, d, tolerance));
end

function value = orient2d(a, b, c)
    value = (b(1) - a(1)) * (c(2) - a(2)) - ...
        (b(2) - a(2)) * (c(1) - a(1));
end

function tf = point_on_segment(point, first, second, tolerance)
    tf = point(1) >= min(first(1), second(1)) - tolerance && ...
        point(1) <= max(first(1), second(1)) + tolerance && ...
        point(2) >= min(first(2), second(2)) - tolerance && ...
        point(2) <= max(first(2), second(2)) + tolerance;
end

function tf = point_in_triangle_2d(point, triangle, tolerance)
    orientations = [orient2d(triangle(1, :), triangle(2, :), point), ...
        orient2d(triangle(2, :), triangle(3, :), point), ...
        orient2d(triangle(3, :), triangle(1, :), point)];
    tf = all(orientations >= -tolerance) || ...
        all(orientations <= tolerance);
end
